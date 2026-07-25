import json
import math
import re
from pathlib import Path

import chromadb
import torch
import torch.nn.functional as F
from chromadb.errors import ChromaError, NotFoundError
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import SiglipModel, SiglipProcessor

from image_index import (
    HNSW_CONFIGURATION,
    IMAGE_COLLECTION_NAME,
    build_image_search_collection,
)
from paths import (
    BGE_M3_MODEL_ID,
    FINAL_IMAGES_DIR,
    FINAL_PROCESSING_REPORT_PATH,
    SIGLIP_MODEL_DIR,
    TEXT_CHUNKS_PATH,
    TEXT_IMAGE_MAPPING_REPORT_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
    project_relative,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COLLECTION_NAME = "doosan_manual_collection"
TEXT_STAGING_COLLECTION_NAME = f"{COLLECTION_NAME}_building"
IMAGE_STAGING_COLLECTION_NAME = f"{IMAGE_COLLECTION_NAME}_building"
TEXT_BACKUP_COLLECTION_NAME = f"{COLLECTION_NAME}_backup"
IMAGE_BACKUP_COLLECTION_NAME = f"{IMAGE_COLLECTION_NAME}_backup"

MAX_DISTANCE = 300.0
TOP_N_IMAGES = 2
SIGLIP_KEEP_THRESHOLD = 0.40

# Five and 95 percentile values from the pilot image-text pair distribution.
SIGLIP_COSINE_LOW = -0.03492925
SIGLIP_COSINE_HIGH = 0.09054340
SIGLIP_TEXT_MAX_CHARS = 1200
SIGLIP_IMAGE_BATCH_SIZE = 16
SIGLIP_TEXT_BATCH_SIZE = 32
CHROMA_BATCH_SIZE = 50


def calculate_2d_distance(text_bboxes, img_bbox, image_page=None):
    """Calculate center distance using only text BBoxes on the image page."""
    page_bboxes = [
        bbox
        for bbox in text_bboxes
        if "coord" in bbox
        and (image_page is None or int(bbox.get("page", image_page)) == int(image_page))
    ]
    if not page_bboxes:
        return 9999.0

    min_x = min(bbox["coord"][0] for bbox in page_bboxes)
    min_y = min(bbox["coord"][1] for bbox in page_bboxes)
    max_x = max(bbox["coord"][2] for bbox in page_bboxes)
    max_y = max(bbox["coord"][3] for bbox in page_bboxes)

    text_center_x = (min_x + max_x) / 2
    text_center_y = (min_y + max_y) / 2
    image_center_x = (img_bbox["x0"] + img_bbox["x1"]) / 2
    image_center_y = (img_bbox["y0"] + img_bbox["y1"]) / 2

    distance = math.hypot(
        text_center_x - image_center_x,
        text_center_y - image_center_y,
    )
    if image_center_y > text_center_y:
        distance *= 0.8
    return distance


def check_explicit_caption(text):
    """Return whether text explicitly refers to a numbered figure or diagram."""
    pattern = r"(그림|도면|도표|도식|Fig\.?|Figure)\s*\d+"
    return re.search(pattern, text, re.IGNORECASE) is not None


def build_siglip_text_prompt(chunk):
    text = re.sub(r"\s+", " ", chunk["text"]).strip()
    heading = re.sub(r"\s+", " ", chunk.get("heading", "")).strip()
    prompt = f"{heading}. {text}" if heading else text
    return prompt[:SIGLIP_TEXT_MAX_CHARS]


def load_siglip_resources():
    if not SIGLIP_MODEL_DIR.exists():
        raise FileNotFoundError(
            f"SigLIP 모델 폴더가 없습니다: {SIGLIP_MODEL_DIR}\n"
            "`python scripts/download_siglip.py`를 먼저 실행하세요."
        )

    print(f"[{DEVICE}] SigLIP 모델을 로컬 폴더에서 불러오는 중입니다.")
    processor = SiglipProcessor.from_pretrained(
        str(SIGLIP_MODEL_DIR),
        local_files_only=True,
    )
    model = SiglipModel.from_pretrained(
        str(SIGLIP_MODEL_DIR),
        local_files_only=True,
    ).to(DEVICE)
    model.eval()
    return processor, model


def extract_feature_tensor(features):
    if isinstance(features, torch.Tensor):
        return features
    if hasattr(features, "pooler_output"):
        return features.pooler_output
    if hasattr(features, "last_hidden_state"):
        return features.last_hidden_state[:, 0]
    raise TypeError(f"지원하지 않는 SigLIP feature 형식입니다: {type(features)}")


def precompute_siglip_image_features(image_metadata, processor, model):
    print("SigLIP 이미지 특징을 배치 단위로 계산하는 중입니다.")
    image_features = {}
    batch_names = []
    batch_images = []

    def flush_batch():
        if not batch_images:
            return

        inputs = processor(images=batch_images, return_tensors="pt").to(DEVICE)
        with torch.inference_mode():
            features = extract_feature_tensor(model.get_image_features(**inputs))
            features = F.normalize(features, p=2, dim=-1).detach().cpu()

        for file_name, feature in zip(batch_names, features):
            image_features[file_name] = feature

        batch_names.clear()
        batch_images.clear()

    for image_metadata_item in image_metadata:
        image_path = FINAL_IMAGES_DIR / image_metadata_item["file_name"]
        if not image_path.exists():
            continue

        with Image.open(image_path) as image:
            batch_images.append(image.convert("RGB"))
        batch_names.append(image_metadata_item["file_name"])

        if len(batch_images) >= SIGLIP_IMAGE_BATCH_SIZE:
            flush_batch()

    flush_batch()
    print(f"SigLIP 이미지 특징 계산 완료: {len(image_features)}개")
    return image_features


def precompute_siglip_text_features(text_chunks, processor, model):
    print("SigLIP 텍스트 특징을 배치 단위로 계산하는 중입니다.")
    prompts = [build_siglip_text_prompt(chunk) for chunk in text_chunks]
    text_features = []

    for start in range(0, len(prompts), SIGLIP_TEXT_BATCH_SIZE):
        batch = prompts[start : start + SIGLIP_TEXT_BATCH_SIZE]
        inputs = processor(
            text=batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
        ).to(DEVICE)
        with torch.inference_mode():
            features = extract_feature_tensor(model.get_text_features(**inputs))
            features = F.normalize(features, p=2, dim=-1).detach().cpu()
        text_features.extend(features)

    print(f"SigLIP 텍스트 특징 계산 완료: {len(text_features)}개")
    return text_features


def calculate_siglip_image_text_scores(
    text_feature,
    candidates,
    model,
    image_features,
):
    valid_candidates = []
    valid_features = []

    for candidate in candidates:
        feature = image_features.get(candidate["file_name"])
        if feature is None:
            candidate["siglip_cosine"] = 0.0
            candidate["siglip_raw_logit"] = 0.0
            candidate["siglip_probability"] = 0.0
            candidate["image_text_similarity"] = 0.0
            candidate["image_missing"] = True
            continue
        valid_candidates.append(candidate)
        valid_features.append(feature)

    if not valid_features:
        return

    image_matrix = torch.stack(valid_features)
    cosine_scores = image_matrix @ text_feature
    logits = cosine_scores
    if hasattr(model, "logit_scale"):
        logits = logits * model.logit_scale.exp().detach().cpu()
    if hasattr(model, "logit_bias"):
        logits = logits + model.logit_bias.detach().cpu()
    probabilities = torch.sigmoid(logits).tolist()

    for candidate, cosine, logit, probability in zip(
        valid_candidates,
        cosine_scores.tolist(),
        logits.tolist(),
        probabilities,
    ):
        candidate["siglip_cosine"] = float(cosine)
        candidate["siglip_raw_logit"] = float(logit)
        candidate["siglip_probability"] = float(probability)
        candidate["image_text_similarity"] = normalize_siglip_cosine(cosine)
        candidate["image_missing"] = False


def calculate_distance_score(distance):
    if distance >= MAX_DISTANCE:
        return 0.0
    return max(0.0, 1.0 - (distance / MAX_DISTANCE))


def normalize_siglip_cosine(cosine):
    span = SIGLIP_COSINE_HIGH - SIGLIP_COSINE_LOW
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (float(cosine) - SIGLIP_COSINE_LOW) / span))


def _delete_collection_if_exists(client, collection_name):
    try:
        client.delete_collection(name=collection_name)
    except NotFoundError:
        pass


def _collection_or_none(client, collection_name):
    try:
        return client.get_collection(name=collection_name)
    except NotFoundError:
        return None


def _promote_collection_pair(client):
    replacements = [
        (
            TEXT_STAGING_COLLECTION_NAME,
            COLLECTION_NAME,
            TEXT_BACKUP_COLLECTION_NAME,
        ),
        (
            IMAGE_STAGING_COLLECTION_NAME,
            IMAGE_COLLECTION_NAME,
            IMAGE_BACKUP_COLLECTION_NAME,
        ),
    ]

    staging = {
        staging_name: client.get_collection(name=staging_name)
        for staging_name, _, _ in replacements
    }
    previous = {}
    promoted = []

    try:
        for _, final_name, backup_name in replacements:
            _delete_collection_if_exists(client, backup_name)
            current = _collection_or_none(client, final_name)
            if current is not None:
                current.modify(name=backup_name)
                previous[final_name] = backup_name

        for staging_name, final_name, _ in replacements:
            staging[staging_name].modify(name=final_name)
            promoted.append(final_name)
    except ChromaError:
        for final_name in promoted:
            _delete_collection_if_exists(client, final_name)
        for final_name, backup_name in previous.items():
            backup = _collection_or_none(client, backup_name)
            if backup is not None:
                backup.modify(name=final_name)
        raise

    for backup_name in previous.values():
        _delete_collection_if_exists(client, backup_name)


def _report_candidate(candidate):
    return {
        "file_name": candidate["file_name"],
        "page": candidate["page"],
        "distance": round(candidate["distance"], 2),
        "distance_score": round(candidate["distance_score"], 6),
        "spatial_candidate": candidate["distance"] < MAX_DISTANCE,
        "image_text_similarity": round(candidate["image_text_similarity"], 6),
        "siglip_cosine": round(candidate["siglip_cosine"], 6),
        "siglip_raw_logit": round(candidate["siglip_raw_logit"], 6),
        "siglip_probability": round(candidate["siglip_probability"], 6),
        "diagram_siglip_score": round(candidate["diagram_siglip_score"], 6),
        "mapping_score": round(candidate["mapping_score"], 6),
    }


def build_multimodal_db_v2(
    text_json=TEXT_CHUNKS_PATH,
    image_json=FINAL_PROCESSING_REPORT_PATH,
    db_path=VECTOR_DB_DIR,
):
    text_chunks = json.loads(Path(text_json).read_text(encoding="utf-8"))
    image_metadata = json.loads(Path(image_json).read_text(encoding="utf-8"))
    if not text_chunks:
        raise ValueError("텍스트 청크가 비어 있습니다.")
    if not image_metadata:
        raise ValueError("이미지 메타데이터가 비어 있습니다.")

    configure_model_cache()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    _delete_collection_if_exists(client, TEXT_STAGING_COLLECTION_NAME)
    text_collection = client.get_or_create_collection(
        name=TEXT_STAGING_COLLECTION_NAME,
        configuration=HNSW_CONFIGURATION,
    )

    embedding_model = SentenceTransformer(
        BGE_M3_MODEL_ID,
        local_files_only=True,
    )
    text_embeddings = embedding_model.encode(
        [chunk["text"] for chunk in text_chunks],
        batch_size=32,
        show_progress_bar=True,
    ).tolist()

    siglip_processor, siglip_model = load_siglip_resources()
    image_features = precompute_siglip_image_features(
        image_metadata,
        siglip_processor,
        siglip_model,
    )
    text_features = precompute_siglip_text_features(
        text_chunks,
        siglip_processor,
        siglip_model,
    )

    images_by_page = {}
    for image in image_metadata:
        images_by_page.setdefault(int(image["page"]), []).append(image)

    mapping_report = []
    upsert_ids = []
    upsert_documents = []
    upsert_embeddings = []
    upsert_metadatas = []
    print("BBox 후보 제한과 SigLIP 의미 순위 기반 매핑을 시작합니다.")

    for index, (chunk, text_feature) in enumerate(zip(text_chunks, text_features)):
        text = chunk["text"]
        chunk_pages = sorted({int(page) for page in chunk.get("pages", [])})
        candidate_pages = set(chunk_pages)
        candidate_pages.update(page + 1 for page in chunk_pages)
        nearby_images = [
            image
            for page in sorted(candidate_pages)
            for image in images_by_page.get(page, [])
        ]

        scored_images = []
        explicit_caption = check_explicit_caption(text)
        for image in nearby_images:
            image_page = int(image["page"])
            distance = calculate_2d_distance(
                chunk.get("bboxes", []),
                image["bbox"],
                image_page=image_page,
            )
            if image_page not in chunk_pages:
                distance += 1000.0
            if explicit_caption:
                distance *= 0.1

            scored_images.append(
                {
                    "file_name": image["file_name"],
                    "page": image_page,
                    "distance": distance,
                    "distance_score": calculate_distance_score(distance),
                    "diagram_siglip_score": float(image.get("siglip_score", 0.0)),
                    "siglip_cosine": 0.0,
                    "siglip_raw_logit": 0.0,
                    "siglip_probability": 0.0,
                    "image_text_similarity": 0.0,
                    "mapping_score": 0.0,
                }
            )

        calculate_siglip_image_text_scores(
            text_feature,
            scored_images,
            siglip_model,
            image_features,
        )
        for candidate in scored_images:
            candidate["mapping_score"] = candidate["image_text_similarity"]

        filtered_images = [
            candidate
            for candidate in scored_images
            if candidate["distance"] < MAX_DISTANCE
            or candidate["image_text_similarity"] >= SIGLIP_KEEP_THRESHOLD
        ]
        filtered_images.sort(
            key=lambda candidate: (
                candidate["mapping_score"],
                -candidate["distance"],
            ),
            reverse=True,
        )
        top_images = filtered_images[:TOP_N_IMAGES]

        image_paths = [
            project_relative(FINAL_IMAGES_DIR / candidate["file_name"])
            for candidate in top_images
        ]
        top_candidates = [_report_candidate(candidate) for candidate in top_images]
        primary = top_images[0] if top_images else {}

        metadata = {
            "heading": chunk["heading"],
            "pages": json.dumps(chunk["pages"]),
            "linked_images": json.dumps(image_paths),
            "diagram_siglip_confidence": float(
                primary.get("diagram_siglip_score", 0.0)
            ),
            "image_text_similarity": float(
                primary.get("image_text_similarity", 0.0)
            ),
            "mapping_score": float(primary.get("mapping_score", 0.0)),
            "mapping_candidates": json.dumps(
                top_candidates,
                ensure_ascii=False,
            ),
            "mapping_method": "bbox_candidate_filter_siglip_cosine_ranking",
        }

        chunk_id = f"chunk_{index}"
        mapping_report.append(
            {
                "chunk_id": chunk_id,
                "heading": chunk["heading"],
                "pages": chunk["pages"],
                "text_preview": text[:250],
                "linked_images": image_paths,
                "top_candidates": top_candidates,
            }
        )
        upsert_ids.append(chunk_id)
        upsert_documents.append(text)
        upsert_embeddings.append(text_embeddings[index])
        upsert_metadatas.append(metadata)

        if index % 50 == 0:
            print(f"매핑 진행: {index}/{len(text_chunks)}")

    for start in range(0, len(upsert_ids), CHROMA_BATCH_SIZE):
        end = start + CHROMA_BATCH_SIZE
        text_collection.upsert(
            ids=upsert_ids[start:end],
            documents=upsert_documents[start:end],
            embeddings=upsert_embeddings[start:end],
            metadatas=upsert_metadatas[start:end],
        )

    image_collection = build_image_search_collection(
        text_chunks=text_chunks,
        image_metadata=image_metadata,
        embedding_model=embedding_model,
        client=client,
        reset=True,
        collection_name=IMAGE_STAGING_COLLECTION_NAME,
    )

    temporary_report = TEXT_IMAGE_MAPPING_REPORT_PATH.with_suffix(".json.tmp")
    temporary_report.write_text(
        json.dumps(mapping_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _promote_collection_pair(client)
    temporary_report.replace(TEXT_IMAGE_MAPPING_REPORT_PATH)

    print(f"텍스트 컬렉션 적재 완료: {len(text_chunks)}개")
    print(f"이미지 컬렉션 적재 완료: {image_collection.count()}개")
    print(f"매핑 보고서 저장: {TEXT_IMAGE_MAPPING_REPORT_PATH}")


if __name__ == "__main__":
    build_multimodal_db_v2()
