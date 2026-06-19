import json
import os
import math
import chromadb
import re
import shutil
import numpy as np
from sentence_transformers import SentenceTransformer

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

# 텍스트 데이터와 이미지 데이터를 불러와 공간적 거리와 캡션 유무를 기준으로 서로 정확히 짝을 지은 후, 이를 AI가 검색할 수 있도록 ChromaDB에 최종 저장하는 총괄 함수
def build_multimodal_db_v2(text_json, img_json, db_path="./rag_db"):
    with open(text_json, "r", encoding="utf-8") as f:
        text_chunks = json.load(f)
    with open(img_json, "r", encoding="utf-8") as f:
        img_metadata = json.load(f)
        
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="doosan_manual_collection")
    
    model = SentenceTransformer('BAAI/bge-m3')
    print(" 2D 공간 거리 및 규칙 기반 정밀 매핑 시작...")

    for i, chunk in enumerate(text_chunks):
        text = chunk["text"]
        emb = model.encode(text).tolist()
        
        page_num = chunk["pages"][0]
        same_page_imgs = [img for img in img_metadata if img['page'] in [page_num, page_num + 1]]
        
        scored_images = []
        is_caption_text = check_explicit_caption(text)
        
        for img in same_page_imgs:
            dist = calculate_2d_distance(chunk["bboxes"], img["bbox"])
            if img['page'] == page_num + 1: 
                dist += 1000.0     # 다음 페이지에 있으면 패널티 부여   
            if is_caption_text: dist *= 0.1     # 가중치
                
            scored_images.append({  # 점수판 기록
                "file_name": img["file_name"],
                "distance": dist,
                "siglip_score": img["siglip_score"]
            })
        
        # 거리순 정렬 후, 거리 임계값 필터링 + 상위 N개만 선택
        scored_images.sort(key=lambda x: x["distance"])
        filtered_images = [si for si in scored_images if si["distance"] < MAX_DISTANCE]
        top_images = filtered_images[:TOP_N_IMAGES]

        # 선별된 이미지만 경로를 생성하여 메타데이터에 저장
        final_img_paths = [os.path.join("final_refined_data", si["file_name"]) for si in top_images]
        primary_score = top_images[0]["siglip_score"] if top_images else 0.0
        
        meta = {
            "heading": chunk["heading"],
            "pages": str(chunk["pages"]),
            "linked_images": json.dumps(final_img_paths),
            "siglip_confidence": primary_score,
            "mapping_method": "2d_spatial_and_rule_based"
        }
        
        collection.add(
            documents=[text], embeddings=[emb], metadatas=[meta], ids=[f"chunk_{i}"]
        )
        if i % 50 == 0: print(f"진행 중: {i}/{len(text_chunks)}")

    print(f"\n 고도화된 매핑 로직 반영 완료! 총 {len(text_chunks)}개 데이터 적재 완료.")

if __name__ == "__main__":
    build_multimodal_db_v2("text_chunks.json", "final_processing_report.json")