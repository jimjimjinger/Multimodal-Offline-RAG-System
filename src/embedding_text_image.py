import json
import math
import chromadb
import re
import torch
import torch.nn.functional as F
from pathlib import Path
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import SiglipProcessor, SiglipModel
from image_index import IMAGE_COLLECTION_NAME, build_image_search_collection
from paths import (
    FINAL_IMAGES_DIR,
    FINAL_PROCESSING_REPORT_PATH,
    SIGLIP_MODEL_DIR,
    TEXT_IMAGE_MAPPING_REPORT_PATH,
    TEXT_CHUNKS_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
    project_relative,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COLLECTION_NAME = "doosan_manual_collection"
HNSW_CONFIGURATION = {"hnsw": {"sync_threshold": 100}}

# 텍스트 영역의 중심점과 도면 영역의 중심점을 계산하여 두 객체 간의 2차원 물리적 최단 거리를 측정하고, 이미지가 텍스트 아래에 있을 경우 가산점을 부여하는 함수
def calculate_2d_distance(text_bboxes, img_bbox):
    if not text_bboxes: return 9999.0
    
    min_x = min([b['coord'][0] for b in text_bboxes])
    min_y = min([b['coord'][1] for b in text_bboxes])
    max_x = max([b['coord'][2] for b in text_bboxes])
    max_y = max([b['coord'][3] for b in text_bboxes])
    
    text_center_x = (min_x + max_x) / 2
    text_center_y = (min_y + max_y) / 2
    
    img_center_x = (img_bbox['x0'] + img_bbox['x1']) / 2
    img_center_y = (img_bbox['y0'] + img_bbox['y1']) / 2
    
    distance = math.hypot(text_center_x - img_center_x, text_center_y - img_center_y)
    
    # 보통 그림이 아래에 있는것을 판단
    if img_center_y > text_center_y: distance *= 0.8 
    return distance

# 텍스트 내용 중에 "그림 1" 또는 "Fig. 2"와 같이 도면을 직접적으로 가리키는 명시적인 단어가 존재하는지 확인하여 매핑 정확도를 보정하는 함수
def check_explicit_caption(text):
    pattern = r'(그림|도면|Fig\.?|Figure)\s*\d+'
    if re.search(pattern, text, re.IGNORECASE): return True
    return False

# 이미지 매핑 필터링 상수
MAX_DISTANCE = 300.0   # 이 거리를 초과하면 관련 없는 이미지로 판단하여 제외
TOP_N_IMAGES = 2       # 임계값을 통과한 이미지 중 최대 보관 개수
SIGLIP_KEEP_THRESHOLD = 0.40
# 985개 동일/인접 페이지 쌍의 cosine 5/95 percentile. 범위 밖은 0/1로 자른다.
SIGLIP_COSINE_LOW = -0.03492925
SIGLIP_COSINE_HIGH = 0.09054340
SIGLIP_TEXT_MAX_CHARS = 1200
SIGLIP_IMAGE_BATCH_SIZE = 16


def build_siglip_text_prompt(chunk):
    text = re.sub(r"\s+", " ", chunk["text"]).strip()
    heading = re.sub(r"\s+", " ", chunk.get("heading", "")).strip()
    prompt = f"{heading}. {text}" if heading else text
    return prompt[:SIGLIP_TEXT_MAX_CHARS]


def load_siglip_resources():
    if not SIGLIP_MODEL_DIR.exists():
        raise FileNotFoundError(
            f"SigLIP 모델 폴더가 없습니다: {SIGLIP_MODEL_DIR}\n"
            "먼저 `python scripts/download_siglip.py`를 실행하세요."
        )

    print(f"[{DEVICE}] SigLIP image-text similarity 모델 로드 중...")
    processor = SiglipProcessor.from_pretrained(str(SIGLIP_MODEL_DIR))
    model = SiglipModel.from_pretrained(str(SIGLIP_MODEL_DIR)).to(DEVICE)
    model.eval()
    return processor, model


def extract_feature_tensor(features):
    if isinstance(features, torch.Tensor):
        return features
    if hasattr(features, "pooler_output"):
        return features.pooler_output
    if hasattr(features, "last_hidden_state"):
        return features.last_hidden_state[:, 0]
    raise TypeError(f"지원하지 않는 SigLIP feature 반환 형식입니다: {type(features)}")


def precompute_siglip_image_features(img_metadata, processor, model):
    print("SigLIP 이미지 feature 사전 계산 중...")
    image_features = {}
    batch_names = []
    images = []

    def flush_batch():
        if not images:
            return

        inputs = processor(images=images, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            features = extract_feature_tensor(features)
            features = F.normalize(features, p=2, dim=-1).detach().cpu()

        for file_name, feature in zip(batch_names, features):
            image_features[file_name] = feature

        batch_names.clear()
        images.clear()

    for img in img_metadata:
        image_path = FINAL_IMAGES_DIR / img["file_name"]
        if not image_path.exists():
            continue

        with Image.open(image_path) as image:
            images.append(image.convert("RGB"))
        batch_names.append(img["file_name"])

        if len(images) >= SIGLIP_IMAGE_BATCH_SIZE:
            flush_batch()

    flush_batch()
    print(f"SigLIP 이미지 feature 계산 완료: {len(image_features)}개")
    return image_features


def calculate_siglip_image_text_scores(text_prompt, candidates, processor, model, image_features):
    valid_candidates = []
    valid_features = []

    for candidate in candidates:
        feature = image_features.get(candidate["file_name"])
        if feature is None:
            candidate["siglip_cosine"] = 0.0
            candidate["image_text_similarity"] = 0.0
            candidate["image_missing"] = True
            continue

        valid_candidates.append(candidate)
        valid_features.append(feature)

    if not valid_features:
        return

    inputs = processor(
        text=[text_prompt],
        return_tensors="pt",
        padding=True,
        truncation=True,
    ).to(DEVICE)

    with torch.no_grad():
        text_feature = model.get_text_features(**inputs)
        text_feature = extract_feature_tensor(text_feature)
        text_feature = F.normalize(text_feature, p=2, dim=-1).detach().cpu()[0]
        image_matrix = torch.stack(valid_features)
        cosine_scores = image_matrix @ text_feature
        logits = cosine_scores
        if hasattr(model, "logit_scale"):
            logits = logits * model.logit_scale.exp().detach().cpu()
        if hasattr(model, "logit_bias"):
            logits = logits + model.logit_bias.detach().cpu()
        probabilities = torch.sigmoid(logits).detach().cpu().tolist()

    for candidate, cosine, logit, probability in zip(
        valid_candidates,
        cosine_scores.detach().cpu().tolist(),
        logits.detach().cpu().tolist(),
        probabilities,
    ):
        similarity = normalize_siglip_cosine(cosine)
        candidate["siglip_cosine"] = round(float(cosine), 6)
        candidate["siglip_raw_logit"] = round(float(logit), 4)
        candidate["siglip_probability"] = round(float(probability), 6)
        candidate["image_text_similarity"] = round(similarity, 4)
        candidate["image_missing"] = False


def calculate_distance_score(distance):
    if distance >= MAX_DISTANCE:
        return 0.0
    return round(max(0.0, 1.0 - (distance / MAX_DISTANCE)), 4)


def normalize_siglip_cosine(cosine):
    span = SIGLIP_COSINE_HIGH - SIGLIP_COSINE_LOW
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (float(cosine) - SIGLIP_COSINE_LOW) / span))

# BBox로 공간 후보를 제한하고 SigLIP으로 의미 순위를 정한 뒤 ChromaDB에 저장한다.
def build_multimodal_db_v2(text_json=TEXT_CHUNKS_PATH, img_json=FINAL_PROCESSING_REPORT_PATH, db_path=VECTOR_DB_DIR):
    with open(text_json, "r", encoding="utf-8") as f:
        text_chunks = json.load(f)
    with open(img_json, "r", encoding="utf-8") as f:
        img_metadata = json.load(f)
        
    configure_model_cache()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration=HNSW_CONFIGURATION,
    )
    
    embedding_model = SentenceTransformer('BAAI/bge-m3')
    text_embeddings = embedding_model.encode(
        [chunk["text"] for chunk in text_chunks],
        batch_size=32,
        show_progress_bar=True,
    ).tolist()
    siglip_processor, siglip_model = load_siglip_resources()
    siglip_image_features = precompute_siglip_image_features(img_metadata, siglip_processor, siglip_model)
    mapping_report = []
    print("BBox 공간 후보 필터 + SigLIP 의미 순위 기반 매핑 시작...")

    for i, chunk in enumerate(text_chunks):
        text = chunk["text"]
        emb = text_embeddings[i]
        
        page_num = chunk["pages"][0]
        same_page_imgs = [img for img in img_metadata if img['page'] in [page_num, page_num + 1]]
        
        scored_images = []
        is_caption_text = check_explicit_caption(text)
        siglip_text_prompt = build_siglip_text_prompt(chunk)
        
        for img in same_page_imgs:
            dist = calculate_2d_distance(chunk["bboxes"], img["bbox"])
            if img['page'] == page_num + 1: 
                dist += 1000.0     # 다음 페이지에 있으면 패널티 부여   
            if is_caption_text: dist *= 0.1     # 가중치
                
            scored_images.append({  # 점수판 기록
                "file_name": img["file_name"],
                "page": img["page"],
                "distance": dist,
                "distance_score": calculate_distance_score(dist),
                "diagram_siglip_score": img["siglip_score"],
                "siglip_cosine": 0.0,
                "siglip_raw_logit": 0.0,
                "siglip_probability": 0.0,
                "image_text_similarity": 0.0,
                "mapping_score": 0.0,
            })

        calculate_siglip_image_text_scores(
            siglip_text_prompt,
            scored_images,
            siglip_processor,
            siglip_model,
            siglip_image_features,
        )

        for scored_image in scored_images:
            scored_image["mapping_score"] = scored_image["image_text_similarity"]
        
        # BBox는 공간 후보를 제한하고, 후보 간 순위는 SigLIP 의미 유사도로 결정한다.
        filtered_images = [
            si for si in scored_images
            if si["distance"] < MAX_DISTANCE
            or si["image_text_similarity"] >= SIGLIP_KEEP_THRESHOLD
        ]
        filtered_images.sort(key=lambda x: (x["mapping_score"], -x["distance"]), reverse=True)
        top_images = filtered_images[:TOP_N_IMAGES]

        # 선별된 이미지만 경로를 생성하여 메타데이터에 저장
        final_img_paths = [project_relative(FINAL_IMAGES_DIR / si["file_name"]) for si in top_images]
        primary_diagram_score = top_images[0]["diagram_siglip_score"] if top_images else 0.0
        primary_similarity = top_images[0]["image_text_similarity"] if top_images else 0.0
        primary_mapping_score = top_images[0]["mapping_score"] if top_images else 0.0
        top_candidates = [
            {
                "file_name": si["file_name"],
                "page": si["page"],
                "distance": round(si["distance"], 2),
                "distance_score": si["distance_score"],
                "spatial_candidate": si["distance"] < MAX_DISTANCE,
                "image_text_similarity": si["image_text_similarity"],
                "siglip_cosine": si["siglip_cosine"],
                "siglip_raw_logit": si["siglip_raw_logit"],
                "siglip_probability": si["siglip_probability"],
                "diagram_siglip_score": si["diagram_siglip_score"],
                "mapping_score": si["mapping_score"],
            }
            for si in top_images
        ]
        
        meta = {
            "heading": chunk["heading"],
            "pages": str(chunk["pages"]),
            "linked_images": json.dumps(final_img_paths),
            "siglip_confidence": primary_diagram_score,
            "diagram_siglip_confidence": primary_diagram_score,
            "image_text_similarity": primary_similarity,
            "mapping_score": primary_mapping_score,
            "mapping_candidates": json.dumps(top_candidates, ensure_ascii=False),
            "mapping_method": "bbox_candidate_filter_siglip_cosine_ranking"
        }

        mapping_report.append({
            "chunk_id": f"chunk_{i}",
            "heading": chunk["heading"],
            "pages": chunk["pages"],
            "text_preview": text[:250],
            "linked_images": final_img_paths,
            "top_candidates": top_candidates,
        })
        
        collection.upsert(
            documents=[text], embeddings=[emb], metadatas=[meta], ids=[f"chunk_{i}"]
        )
        if i % 50 == 0: print(f"진행 중: {i}/{len(text_chunks)}")

    with open(TEXT_IMAGE_MAPPING_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, indent=2, ensure_ascii=False)

    print(f"{IMAGE_COLLECTION_NAME} 이미지 전용 검색 컬렉션 생성 중...")
    image_collection = build_image_search_collection(
        text_chunks=text_chunks,
        image_metadata=img_metadata,
        embedding_model=embedding_model,
        client=client,
        reset=True,
    )

    print(f"\nSigLIP similarity 매핑 반영 완료! 총 {len(text_chunks)}개 데이터 적재 완료.")
    print(f"매핑 리포트 저장: {TEXT_IMAGE_MAPPING_REPORT_PATH}")
    print(f"{IMAGE_COLLECTION_NAME} 적재 완료: {image_collection.count()}개 이미지")

if __name__ == "__main__":
    build_multimodal_db_v2()
