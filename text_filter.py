import fitz  # PyMuPDF
import re
import numpy as np
import json  # JSON 저장을 위해 추가
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# 1. 물리적 청킹 (좌표 및 페이지 메타데이터 수집 강화)
#    각 span 텍스트와 bbox를 쌍으로 기록하여 의미론적 청킹 시 정확한 bbox 슬라이싱 가능
def get_physical_chunks(pdf_path):
    doc = fitz.open(pdf_path)
    physical_chunks = []

    current_heading = "문서 시작"
    current_body_texts = []
    current_pages = set()
    current_bboxes = []  # 텍스트의 물리적 좌표를 담을 리스트
    current_span_bbox_pairs = []  # (span_text, bbox) 쌍을 기록하여 문장↔bbox 매핑 지원

    HEADER_Y, FOOTER_Y = 50, 780

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        for b in blocks:
            if b['type'] == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text: continue

                        bbox = span["bbox"] # (x0, y0, x1, y1) 형태의 좌표
                        y0 = bbox[1]

                        if y0 < HEADER_Y or y0 > FOOTER_Y: continue # 노이즈 제거

                        font_size = span["size"]
                        font_weight = span["flags"]

                        bbox_record = {
                            "page": page_num + 1,
                            "coord": [round(c, 2) for c in bbox]
                        }

                        # 대제목 감지 로직 (크기가 14 이상이거나 굵은 글씨)
                        if font_size > 14 or (font_size > 12 and font_weight & 2 ** 4):
                            if current_body_texts:
                                physical_chunks.append({
                                    "heading": current_heading,
                                    "text": " ".join(current_body_texts),
                                    "pages": list(current_pages),
                                    "bboxes": current_bboxes,
                                    "span_bbox_pairs": current_span_bbox_pairs  # 문장↔bbox 매핑용
                                })

                            # 새 제목으로 교체 후 데이터 초기화
                            current_heading = text
                            current_body_texts = []
                            current_pages = set()
                            current_bboxes = []
                            current_span_bbox_pairs = []
                        else:
                            # 본문인 경우 텍스트와 함께 페이지, 좌표를 계속 누적
                            current_body_texts.append(text)
                            current_pages.add(page_num + 1)
                            current_bboxes.append(bbox_record)
                            current_span_bbox_pairs.append((text, bbox_record))

    # 마지막 남은 텍스트 덩어리 처리
    if current_body_texts:
        physical_chunks.append({
            "heading": current_heading,
            "text": " ".join(current_body_texts),
            "pages": list(current_pages),
            "bboxes": current_bboxes,
            "span_bbox_pairs": current_span_bbox_pairs
        })

    return physical_chunks

# 문장에 포함된 span을 찾아 해당 bbox만 정확히 추출하는 함수
def find_bboxes_for_sentence(sentence, span_bbox_pairs, used_indices):
    matched_bboxes = []
    for idx, (span_text, bbox) in enumerate(span_bbox_pairs):
        if idx in used_indices:
            continue
        # span 텍스트가 문장 안에 포함되어 있으면 해당 bbox를 매칭
        if span_text in sentence:
            matched_bboxes.append(bbox)
            used_indices.add(idx)
    return matched_bboxes

# 2. 의미론적 청킹 (Sentence-Transformers 적용 및 메타데이터 상속)
#    분할된 문장에 해당하는 bbox만 정확히 슬라이싱하여 상속
def semantic_chunking(physical_chunks, model, similarity_threshold=0.5):
    final_semantic_chunks = []

    for chunk in physical_chunks:
        # 문장 단위 분할 (단순 마침표 기준)
        sentences = re.split(r'(?<=[.!?])\s+', chunk["text"])
        sentences = [s for s in sentences if len(s) > 5]

        if not sentences: continue

        span_bbox_pairs = chunk.get("span_bbox_pairs", [])

        # sentence-transformers 방식의 임베딩 추출
        embeddings = model.encode(sentences)
        current_semantic_group = [sentences[0]]
        current_group_bboxes = []
        current_group_pages = set()
        used_indices = set()  # 이미 매칭된 span 인덱스 추적

        # 첫 번째 문장의 bbox 수집
        matched = find_bboxes_for_sentence(sentences[0], span_bbox_pairs, used_indices)
        current_group_bboxes.extend(matched)
        for b in matched:
            current_group_pages.add(b["page"])

        for i in range(1, len(sentences)):
            # 코사인 유사도 계산
            sim = cosine_similarity([embeddings[i-1]], [embeddings[i]])[0][0]

            # 유사도가 낮아 주제가 바뀔 때 자르기
            if sim < similarity_threshold:
                # 매칭된 bbox가 없으면 원본 전체 bbox를 폴백으로 사용
                final_bboxes = current_group_bboxes if current_group_bboxes else chunk["bboxes"]
                final_pages = list(current_group_pages) if current_group_pages else chunk["pages"]

                final_semantic_chunks.append({
                    "heading": chunk["heading"],
                    "text": " ".join(current_semantic_group),
                    "pages": final_pages,
                    "bboxes": final_bboxes
                })
                current_semantic_group = [sentences[i]]
                current_group_bboxes = []
                current_group_pages = set()

            else:
                current_semantic_group.append(sentences[i])

            # 현재 문장의 bbox 수집
            matched = find_bboxes_for_sentence(sentences[i], span_bbox_pairs, used_indices)
            current_group_bboxes.extend(matched)
            for b in matched:
                current_group_pages.add(b["page"])

        if current_semantic_group:
            final_bboxes = current_group_bboxes if current_group_bboxes else chunk["bboxes"]
            final_pages = list(current_group_pages) if current_group_pages else chunk["pages"]

            final_semantic_chunks.append({
                "heading": chunk["heading"],
                "text": " ".join(current_semantic_group),
                "pages": final_pages,
                "bboxes": final_bboxes
            })

    return final_semantic_chunks

# 3. 전체 파이프라인 실행 및 JSON 저장
if __name__ == "__main__":
    pdf_path = "A-Series.pdf"
    
    print("BGE-M3 모델 로딩 중 (Sentence-Transformers)...")
    bge_m3_model = SentenceTransformer('BAAI/bge-m3')
    
    print("물리적 청킹(좌표 포함) 진행 중...")
    phys_chunks = get_physical_chunks(pdf_path)
    
    print("의미론적 청킹 진행 중... (분량이 많아 수 분 정도 걸릴 수 있습니다 ⏳)")
    # 임계값은 문서 특성에 맞게 조절 가능 (0.4 ~ 0.6 추천)
    final_data = semantic_chunking(phys_chunks, bge_m3_model, similarity_threshold=0.4)
    
    # JSON 저장 로직 반영 (내부 매핑용 span_bbox_pairs는 제거하고 저장)
    if final_data:
        output_data = []
        for chunk in final_data:
            output_data.append({
                "heading": chunk["heading"],
                "text": chunk["text"],
                "pages": chunk["pages"],
                "bboxes": chunk["bboxes"]
            })

        output_filename = "text_chunks.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n성공적으로 '{output_filename}' 파일로 저장되었습니다!")
        print(f"총 {len(final_data)}개의 의미론적 텍스트 덩어리가 추출되었습니다.")
        
        # 첫 번째 청크의 결과물 구조 확인
        print("\n[최종 생성된 JSON 구조 예시 - Chunk 1]")
        print(f"목차(Heading): {final_data[0]['heading']}")
        print(f"포함 페이지: {final_data[0]['pages']}")
        print(f"텍스트 미리보기: {final_data[0]['text'][:80]}...")
    else:
        print("추출된 데이터가 없습니다.")