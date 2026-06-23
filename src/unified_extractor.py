import fitz  # PyMuPDF
import io
import json
import hashlib
import torch
from PIL import Image, ImageStat
from transformers import SiglipProcessor, SiglipModel
from paths import A_SERIES_PDF, FINAL_IMAGES_DIR, FINAL_PROCESSING_REPORT_PATH, SIGLIP_MODEL_DIR

PDF_PATH = A_SERIES_PDF
OUTPUT_DIR = FINAL_IMAGES_DIR
REPORT_PATH = FINAL_PROCESSING_REPORT_PATH
MODEL_PATH = SIGLIP_MODEL_DIR
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MIN_SIZE = 120
ICON_ASPECT_RATIO_TOLERANCE = 0.1
LOGO_FREQUENCY_THRESHOLD = 0.1
MIN_SLICE_HEIGHT = 50 

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 이미지 데이터를 바탕으로 고유한 암호(지문)를 생성하여, 전체 문서에서 똑같은 이미지가 중복해서 등장하는지 식별하는 함수
def get_image_hash(image_bytes):
    return hashlib.md5(image_bytes).hexdigest()

# 아무 의미 없는 투명한 이미지나 단색 배경 등 정보값이 없는 불필요한 이미지를 걸러내는 함수
def is_blank_or_solid_image(image_bytes):
    try:
        img_pil = Image.open(io.BytesIO(image_bytes))
        if img_pil.mode in ('RGBA', 'LA') or (img_pil.mode == 'P' and 'transparency' in img_pil.info):
            alpha = img_pil.convert('RGBA').split()[-1]
            if alpha.getextrema() == (0, 0): 
                return True
                
        width, height = img_pil.size
        if width > 10 and height > 10:
            img_pil = img_pil.crop((5, 5, width-5, height-5))

        img_gray = img_pil.convert("L")
        stat = ImageStat.Stat(img_gray)
        
        if stat.mean[0] > 250 or stat.mean[0] < 5: return True
        if stat.stddev[0] < 5.0: return True
        return False
    except: return False

# 문서 내 글자의 위치를 절취선으로 활용하여, 여러 개가 하나로 뭉쳐진 거대한 이미지를 개별 도면으로 정밀하게 잘라내는 함수
def split_image_by_text_walls(page, image_bytes, img_bbox, ext):
    # 데이터 그림으로 변환
    try: img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except: return [{"bytes": image_bytes, "bbox": img_bbox, "ext": ext, "width": 0, "height": 0}]
    
    # PDF와 실제 이미지 간의 크기 비율(Scale) 계산
    pdf_img_height = img_bbox[3] - img_bbox[1]
    if pdf_img_height <= 0:
        return [{"bytes": image_bytes, "bbox": img_bbox, "ext": ext, "width": img_pil.width, "height": img_pil.height}]

    scale_y = img_pil.height / pdf_img_height
    blocks = page.get_text("blocks")
    cut_zones = []

    for b in blocks:
        if b[6] == 0: 
            bx0, by0, bx1, by1 = b[:4] # 텍스트가 이미지 영역 안에 들어와 있는지 확인
            if bx1 > img_bbox[0] and bx0 < img_bbox[2]:
                if by0 > img_bbox[1] + 5 and by1 < img_bbox[3] - 5:
                    cut_zones.append((by0, by1))

    if not cut_zones:
        return [{"bytes": image_bytes, "bbox": img_bbox, "ext": ext, "width": img_pil.width, "height": img_pil.height}]

    cut_zones.sort(key=lambda x: x[0])# 위에서부터 아래로 순서대로 정렬
    merged_cuts = [cut_zones[0]]
    # 이전 글자와 지금 글자가 5포인트 이내로 바짝 붙어있다면 한 덩어리로 합침
    for current in cut_zones[1:]:
        prev = merged_cuts[-1]
        if current[0] <= prev[1] + 5: 
            merged_cuts[-1] = (prev[0], max(prev[1], current[1]))
        else:
            merged_cuts.append(current)

    sub_images = []
    current_pdf_y = img_bbox[1]

    for cut in merged_cuts:
        text_top, text_bottom = cut[0], cut[1]
        part_pdf_height = text_top - current_pdf_y
        
        # 조각이 너무 작지 않은지 확인
        if part_pdf_height > (MIN_SLICE_HEIGHT / scale_y):
            crop_y0 = int((current_pdf_y - img_bbox[1]) * scale_y)
            crop_y1 = int((text_top - img_bbox[1]) * scale_y)
            
            # 자르기
            cropped_pil = img_pil.crop((0, crop_y0, img_pil.width, crop_y1))
            img_byte_arr = io.BytesIO()
            cropped_pil.save(img_byte_arr, format='PNG')
            
            sub_images.append({
                "bytes": img_byte_arr.getvalue(),
                "bbox": [img_bbox[0], current_pdf_y, img_bbox[2], text_top],
                "ext": "png", "width": cropped_pil.width, "height": cropped_pil.height
            })
        current_pdf_y = text_bottom 

    # 마지막 글자를 자르고도 밑에 이미지가 넉넉히 남아있다면 자르고 담기
    if img_bbox[3] - current_pdf_y > (MIN_SLICE_HEIGHT / scale_y):
        crop_y0 = int((current_pdf_y - img_bbox[1]) * scale_y)
        crop_y1 = img_pil.height
        
        cropped_pil = img_pil.crop((0, crop_y0, img_pil.width, crop_y1))
        img_byte_arr = io.BytesIO()
        cropped_pil.save(img_byte_arr, format='PNG')
        
        sub_images.append({
            "bytes": img_byte_arr.getvalue(),
            "bbox": [img_bbox[0], current_pdf_y, img_bbox[2], img_bbox[3]],
            "ext": "png", "width": cropped_pil.width, "height": cropped_pil.height
        })
    return sub_images

# PDF에서 이미지를 추출하고, 자르고, 필터링한 뒤 SigLIP으로 진짜 도면만 판별하여 저장하는 전체 공정을 순서대로 지휘하는 메인 총괄 함수
def run_unified_pipeline():
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    
    print(f"[{DEVICE}] 환경에서 SigLIP 모델을 로드 중...")
    processor = SiglipProcessor.from_pretrained(str(MODEL_PATH))
    model = SiglipModel.from_pretrained(str(MODEL_PATH)).to(DEVICE)
    candidate_labels = ["a blank white page or empty background", "a technical robot diagram or engineering schematic"]

    raw_extracted_images = []
    occurrence_map = {}

    print(f"\n[Step 1] PDF 전체 순회 및 도면 쪼개기 진행 (총 {total_pages}페이지)")
    for page_index in range(total_pages):
        page = doc[page_index]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            image_rects = page.get_image_rects(xref)
            bbox = [image_rects[0].x0, image_rects[0].y0, image_rects[0].x1, image_rects[0].y1] if image_rects else [0, 0, 0, 0]
            
            sliced_images = split_image_by_text_walls(page, image_bytes, bbox, base_image["ext"])
            
            for sub_idx, sub_img in enumerate(sliced_images):
                img_hash = get_image_hash(sub_img["bytes"])
                obj_key = (img_hash, sub_img["width"], sub_img["height"])
                occurrence_map[obj_key] = occurrence_map.get(obj_key, 0) + 1
                
                raw_extracted_images.append({
                    "page": page_index + 1,
                    "img_index": f"{img_index}_{sub_idx}", 
                    "bytes": sub_img["bytes"],
                    "ext": sub_img["ext"],
                    "width": sub_img["width"],
                    "height": sub_img["height"],
                    "bbox": sub_img["bbox"],
                    "key": obj_key
                })

    print(f"\n[Step 2 & 3] 하드 필터링 및 SigLIP 시맨틱 분석 진행 중...")
    final_metadata = []
    stats = {"hard_blank": 0, "hard_logo": 0, "hard_icon": 0, "siglip_rejected": 0, "saved": 0}

    for img_data in raw_extracted_images:
        if is_blank_or_solid_image(img_data["bytes"]):
            stats["hard_blank"] += 1
            continue

        appearance_rate = occurrence_map[img_data["key"]] / total_pages
        if appearance_rate > LOGO_FREQUENCY_THRESHOLD:
            stats["hard_logo"] += 1
            continue

        aspect_ratio = img_data["width"] / img_data["height"]
        is_small = img_data["width"] < MIN_SIZE or img_data["height"] < MIN_SIZE
        is_square = abs(aspect_ratio - 1.0) < ICON_ASPECT_RATIO_TOLERANCE
        if is_small and is_square:
            stats["hard_icon"] += 1
            continue

        image_pil = Image.open(io.BytesIO(img_data["bytes"])).convert("RGB")
        inputs = processor(text=candidate_labels, images=image_pil, return_tensors="pt", padding=True).to(DEVICE)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)
        
        is_diagram_prob = probs[0][1].item()

        if is_diagram_prob > 0.5:
            file_name = f"page_{img_data['page']}_img_{img_data['img_index']}.{img_data['ext']}"
            save_path = OUTPUT_DIR / file_name
            
            with open(save_path, "wb") as f:
                f.write(img_data["bytes"])
            
            final_metadata.append({
                "file_name": file_name,
                "page": img_data["page"],
                "bbox": {"x0": img_data["bbox"][0], "y0": img_data["bbox"][1], "x1": img_data["bbox"][2], "y1": img_data["bbox"][3]},
                "siglip_score": round(is_diagram_prob, 4)
            })
            stats["saved"] += 1
        else:
            stats["siglip_rejected"] += 1

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, indent=4, ensure_ascii=False)

    print("\n[최종 합격] 고순도 도면 저장:", stats['saved'], "개 완료")

if __name__ == "__main__":
    run_unified_pipeline()
