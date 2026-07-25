import argparse
import csv
import hashlib
import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_scie_retrieval import is_text_match  # noqa: E402
from paths import (  # noqa: E402
    BGE_M3_MODEL_ID,
    FINAL_PROCESSING_REPORT_PATH,
    SCIE_DATA_DIR,
    SCIE_DIR,
    STAGE_CONTEXT_MAP_MANUAL_PATH,
    TEXT_CHUNKS_PATH,
    TEXT_IMAGE_MAPPING_REPORT_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
)
from rag_search import (  # noqa: E402
    IMAGE_COLLECTION_NAME,
    TEXT_COLLECTION_NAME,
    extract_pages,
    load_stage_context_map,
    page_range_score,
    term_match_score,
)
from stage_classifier import build_stage_profiles  # noqa: E402


OUTPUT_DIR = SCIE_DIR / "weight_optimization"
OUTPUT_PATH = OUTPUT_DIR / "retrieval_feature_cache.pkl"
QUESTION_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"

IMAGE_TEXT_TOP_K = 60
IMAGE_COLLECTION_TOP_K = 80
STAGE_IMAGE_TOP_K = 80
STAGE_TEXT_TOP_K = 30
TEXT_RANK_SCORE_WINDOW = 30
STAGE_RANK_SCORE_WINDOW = 80
SEMANTIC_ANSWER_TOP_K = 20
SEMANTIC_ACCEPT_RANK = 15


def read_questions():
    with QUESTION_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hashes():
    return {
        "questions_sha256": file_sha256(QUESTION_PATH),
        "text_chunks_sha256": file_sha256(TEXT_CHUNKS_PATH),
        "mapping_report_sha256": file_sha256(TEXT_IMAGE_MAPPING_REPORT_PATH),
        "image_metadata_sha256": file_sha256(FINAL_PROCESSING_REPORT_PATH),
        "stage_context_sha256": file_sha256(STAGE_CONTEXT_MAP_MANUAL_PATH),
    }


def parse_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def distance_to_score(distance):
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(0.0, float(distance)))


def normalize_rows(values):
    values = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


def image_collection_documents(collection):
    result = collection.get(include=["metadatas", "documents"])
    records = {}
    for meta, document in zip(result.get("metadatas") or [], result.get("documents") or []):
        file_name = meta.get("file_name")
        if file_name:
            records[file_name] = {
                "meta": meta,
                "document": document or "",
            }
    return records


def image_index_data(images, image_documents):
    names = [image["file_name"] for image in images]
    name_to_index = {name: index for index, name in enumerate(names)}
    by_page = {}
    candidate_text = []
    candidate_pages = []
    diagram_confidence = np.zeros(len(images), dtype=np.float32)

    for index, image in enumerate(images):
        page = int(image["page"])
        by_page.setdefault(page, []).append(index)
        record = image_documents.get(image["file_name"], {})
        meta = record.get("meta", {})
        document = record.get("document", "")
        headings = parse_json(meta.get("source_headings"), [])
        source_pages = parse_json(meta.get("source_pages"), [])
        candidate_text.append(
            " ".join(
                [
                    image["file_name"],
                    " ".join(str(value) for value in headings),
                    document,
                ]
            ).lower()
        )
        pages = {page}
        pages.update(int(value) for value in source_pages if str(value).isdigit())
        candidate_pages.append(pages)
        diagram_confidence[index] = float(image.get("siglip_score", 0.0))

    return names, name_to_index, by_page, candidate_text, candidate_pages, diagram_confidence


def classify_all(question_embeddings, profiles, profile_embeddings):
    question_vectors = normalize_rows(question_embeddings)
    profile_vectors = normalize_rows(profile_embeddings)
    similarities = question_vectors @ profile_vectors.T
    results = []
    for scores in similarities:
        order = np.argsort(-scores)
        best_index = int(order[0])
        second_score = float(scores[order[1]]) if len(order) > 1 else 0.0
        results.append(
            {
                "predicted_stage": profiles[best_index]["stage"],
                "score": float(scores[best_index]),
                "margin": float(scores[best_index] - second_score),
                "top5": [
                    {
                        "stage": profiles[int(index)]["stage"],
                        "score": float(scores[int(index)]),
                    }
                    for index in order[:5]
                ],
            }
        )
    return results


def result_row(result, query_index, key):
    values = result.get(key) or []
    return values[query_index] if query_index < len(values) else []


def build_static_image_features(
    query_index,
    text_result,
    image_result,
    stage_image_result,
    images,
    image_by_page,
    name_to_index,
    diagram_confidence,
):
    image_count = len(images)
    image_search = np.zeros(image_count, dtype=np.float32)
    page_score = np.zeros(image_count, dtype=np.float32)
    stage_query_score = np.zeros(image_count, dtype=np.float32)
    stage_rank_score = np.zeros(image_count, dtype=np.float32)
    base_mask = np.zeros(image_count, dtype=bool)
    stage_source_mask = np.zeros(image_count, dtype=bool)
    base_sources = [set() for _ in range(image_count)]

    image_metas = result_row(image_result, query_index, "metadatas")
    image_distances = result_row(image_result, query_index, "distances")
    for rank, meta in enumerate(image_metas, start=1):
        image_index = name_to_index.get(meta.get("file_name"))
        if image_index is None:
            continue
        distance = image_distances[rank - 1] if rank - 1 < len(image_distances) else None
        image_search[image_index] = max(image_search[image_index], distance_to_score(distance))
        base_mask[image_index] = True
        base_sources[image_index].add(f"image_db_{rank}")

    text_ids = result_row(text_result, query_index, "ids")
    text_metas = result_row(text_result, query_index, "metadatas")
    retrieved_chunks = []
    for rank, (chunk_id, meta) in enumerate(zip(text_ids, text_metas), start=1):
        rank_score = max(0.0, 1.0 - ((rank - 1) / max(1, TEXT_RANK_SCORE_WINDOW)))
        retrieved_chunks.append(
            {
                "chunk_id": chunk_id,
                "rank": rank,
                "rank_score": rank_score,
            }
        )
        pages = extract_pages(meta.get("pages"))
        for candidate_page in {page + gap for page in pages for gap in (-1, 0, 1) if page + gap > 0}:
            for image_index in image_by_page.get(candidate_page, []):
                page_gap = min(abs(candidate_page - page) for page in pages)
                multiplier = 1.0 if page_gap == 0 else 0.82
                page_score[image_index] = max(page_score[image_index], rank_score * multiplier)
                base_mask[image_index] = True
                base_sources[image_index].add(f"page_neighbor_{rank}")

    stage_metas = result_row(stage_image_result, query_index, "metadatas")
    stage_distances = result_row(stage_image_result, query_index, "distances")
    for rank, meta in enumerate(stage_metas, start=1):
        image_index = name_to_index.get(meta.get("file_name"))
        if image_index is None:
            continue
        distance = stage_distances[rank - 1] if rank - 1 < len(stage_distances) else None
        stage_query_score[image_index] = max(stage_query_score[image_index], distance_to_score(distance))
        rank_score = max(0.0, 1.0 - ((rank - 1) / max(1, STAGE_RANK_SCORE_WINDOW)))
        stage_rank_score[image_index] = max(stage_rank_score[image_index], rank_score)
        stage_source_mask[image_index] = True

    return {
        "image_search": image_search,
        "page_score": page_score,
        "diagram_confidence": diagram_confidence.copy(),
        "base_mask": base_mask,
        "base_source_count": np.asarray([len(sources) for sources in base_sources], dtype=np.int16),
        "stage_query_score": stage_query_score,
        "stage_rank_score": stage_rank_score,
        "stage_source_mask": stage_source_mask,
        "retrieved_chunks": retrieved_chunks,
    }


def build_stage_image_features(
    static,
    stage_context,
    image_by_page,
    candidate_pages,
    candidate_text,
):
    image_count = len(candidate_text)
    stage_map_mask = np.zeros(image_count, dtype=bool)
    stage_page = np.zeros(image_count, dtype=np.float32)
    stage_keyword = np.zeros(image_count, dtype=np.float32)
    stage_section = np.zeros(image_count, dtype=np.float32)

    if not stage_context:
        return {
            "stage_map_mask": stage_map_mask,
            "stage_page": stage_page,
            "stage_keyword": stage_keyword,
            "stage_section": stage_section,
        }

    for start, end in stage_context.get("image_ranges", []):
        for page in range(start, end + 1):
            for image_index in image_by_page.get(page, []):
                stage_map_mask[image_index] = True

    keyword_terms = stage_context.get("content_terms", []) + stage_context.get("action_terms", [])
    section_terms = stage_context.get("section_terms", [])
    for image_index in range(image_count):
        stage_page[image_index] = page_range_score(
            candidate_pages[image_index],
            stage_context.get("image_ranges", []),
        )
        stage_keyword[image_index] = term_match_score(
            keyword_terms,
            candidate_text[image_index],
        )[0]
        stage_section[image_index] = term_match_score(
            section_terms,
            candidate_text[image_index],
        )[0]

    return {
        "stage_map_mask": stage_map_mask,
        "stage_page": stage_page,
        "stage_keyword": stage_keyword,
        "stage_section": stage_section,
    }


def build_text_features(
    query_index,
    text_result,
    semantic_answer_result,
    question,
    stage_context,
):
    ids = result_row(text_result, query_index, "ids")[:STAGE_TEXT_TOP_K]
    docs = result_row(text_result, query_index, "documents")[:STAGE_TEXT_TOP_K]
    metas = result_row(text_result, query_index, "metadatas")[:STAGE_TEXT_TOP_K]
    semantic_ids = result_row(semantic_answer_result, query_index, "ids")
    semantic_rank = {doc_id: rank for rank, doc_id in enumerate(semantic_ids, start=1)}

    total = max(1, len(ids))
    base_rank = np.asarray(
        [1.0 - (rank / total) for rank in range(len(ids))],
        dtype=np.float32,
    )
    relevance = np.zeros(len(ids), dtype=bool)
    stage_page = np.zeros(len(ids), dtype=np.float32)
    stage_keyword = np.zeros(len(ids), dtype=np.float32)
    stage_section = np.zeros(len(ids), dtype=np.float32)

    for index, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
        relevance[index] = is_text_match(
            expected_answer=question["정답 텍스트"],
            expected_page=question["페이지"],
            doc=doc,
            meta=meta,
            semantic_rank=semantic_rank.get(doc_id),
        )[0]
        if not stage_context:
            continue

        text = " ".join(
            [
                str(meta.get("heading", "")),
                str(meta.get("pages", "")),
                str(doc or ""),
            ]
        ).lower()
        pages = set(extract_pages(meta.get("pages")))
        stage_page[index] = page_range_score(pages, stage_context.get("text_ranges", []))
        stage_keyword[index] = term_match_score(
            stage_context.get("content_terms", []) + stage_context.get("action_terms", []),
            text,
        )[0]
        stage_section[index] = term_match_score(stage_context.get("section_terms", []), text)[0]

    return {
        "ids": ids,
        "base_rank": base_rank,
        "relevance": relevance,
        "stage_page": stage_page,
        "stage_keyword": stage_keyword,
        "stage_section": stage_section,
    }


def main(force=False):
    configure_model_cache()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    current_hashes = source_hashes()
    if OUTPUT_PATH.exists() and not force:
        try:
            with OUTPUT_PATH.open("rb") as handle:
                existing = pickle.load(handle)
        except (OSError, pickle.PickleError, EOFError):
            existing = {}
        cached_hashes = existing.get("metadata", {}).get("source_hashes", {})
        if cached_hashes == current_hashes:
            print(f"Cache is current: {OUTPUT_PATH}")
            return
        print("Input data changed; rebuilding the retrieval feature cache.")

    questions = read_questions()
    images = json.loads(FINAL_PROCESSING_REPORT_PATH.read_text(encoding="utf-8"))
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection = client.get_collection(name=TEXT_COLLECTION_NAME)
    image_collection = client.get_collection(name=IMAGE_COLLECTION_NAME)
    image_documents = image_collection_documents(image_collection)
    (
        image_names,
        name_to_index,
        image_by_page,
        candidate_text,
        candidate_pages,
        diagram_confidence,
    ) = image_index_data(images, image_documents)

    print("Loading BGE-M3...", flush=True)
    embedder = SentenceTransformer(BGE_M3_MODEL_ID, local_files_only=True)
    question_texts = [question["질문"] for question in questions]
    answer_texts = [question["정답 텍스트"] for question in questions]
    question_embeddings = embedder.encode(question_texts, batch_size=16, show_progress_bar=True)

    profiles = build_stage_profiles(STAGE_CONTEXT_MAP_MANUAL_PATH)
    profile_embeddings = embedder.encode(
        [profile["profile_text"] for profile in profiles],
        batch_size=16,
        show_progress_bar=True,
    )
    classifications = classify_all(question_embeddings, profiles, profile_embeddings)
    stage_queries = [
        f"{classification['predicted_stage']} {question['질문']}"
        for question, classification in zip(questions, classifications)
    ]
    stage_embeddings = embedder.encode(stage_queries, batch_size=16, show_progress_bar=True)
    answer_embeddings = embedder.encode(answer_texts, batch_size=16, show_progress_bar=True)

    print("Querying text and image collections...", flush=True)
    text_result = text_collection.query(
        query_embeddings=np.asarray(question_embeddings).tolist(),
        n_results=IMAGE_TEXT_TOP_K,
    )
    image_result = image_collection.query(
        query_embeddings=np.asarray(question_embeddings).tolist(),
        n_results=IMAGE_COLLECTION_TOP_K,
    )
    stage_image_result = image_collection.query(
        query_embeddings=np.asarray(stage_embeddings).tolist(),
        n_results=STAGE_IMAGE_TOP_K,
    )
    semantic_answer_result = text_collection.query(
        query_embeddings=np.asarray(answer_embeddings).tolist(),
        n_results=SEMANTIC_ANSWER_TOP_K,
    )

    context_map = load_stage_context_map(str(STAGE_CONTEXT_MAP_MANUAL_PATH))
    records = []
    for query_index, (question, classification) in enumerate(zip(questions, classifications)):
        predicted_stage = classification["predicted_stage"]
        stage_context = context_map.get(predicted_stage)
        static = build_static_image_features(
            query_index,
            text_result,
            image_result,
            stage_image_result,
            images,
            image_by_page,
            name_to_index,
            diagram_confidence,
        )
        stage_features = build_stage_image_features(
            static,
            stage_context,
            image_by_page,
            candidate_pages,
            candidate_text,
        )
        text_features = build_text_features(
            query_index,
            text_result,
            semantic_answer_result,
            question,
            stage_context,
        )
        expected_image_index = name_to_index[question["정답 이미지"]]
        records.append(
            {
                "question_id": question["질문 번호"],
                "question": question["질문"],
                "category": question["구분"],
                "question_type": question["질문 유형"],
                "expected_image": question["정답 이미지"],
                "expected_image_index": expected_image_index,
                "expected_stage": question["실습 단계"],
                "classification": classification,
                "stage_context_weight": float(stage_context.get("weight", 1.0)) if stage_context else 1.0,
                "image": {**static, **stage_features},
                "text": text_features,
            }
        )
        print(f"[feature cache] {query_index + 1}/{len(questions)} {question['질문 번호']}", flush=True)

    output = {
        "metadata": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "question_count": len(questions),
            "image_count": len(images),
            "image_text_top_k": IMAGE_TEXT_TOP_K,
            "image_collection_top_k": IMAGE_COLLECTION_TOP_K,
            "stage_image_top_k": STAGE_IMAGE_TOP_K,
            "stage_text_top_k": STAGE_TEXT_TOP_K,
            "semantic_answer_top_k": SEMANTIC_ANSWER_TOP_K,
            "semantic_accept_rank": SEMANTIC_ACCEPT_RANK,
            "source_hashes": current_hashes,
        },
        "image_names": image_names,
        "records": records,
    }
    temporary_path = OUTPUT_PATH.with_suffix(".pkl.tmp")
    with temporary_path.open("wb") as handle:
        pickle.dump(output, handle, protocol=pickle.HIGHEST_PROTOCOL)
    temporary_path.replace(OUTPUT_PATH)
    print(f"Created: {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cache retrieval features for reproducible weight optimization.")
    parser.add_argument("--force", action="store_true", help="Rebuild an existing cache.")
    arguments = parser.parse_args()
    main(force=arguments.force)
