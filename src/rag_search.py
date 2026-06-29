import json
import re
from functools import lru_cache
from pathlib import Path

from image_index import IMAGE_COLLECTION_NAME
from paths import FINAL_IMAGES_DIR, FINAL_PROCESSING_REPORT_PATH, resolve_image_path


TEXT_COLLECTION_NAME = "doosan_manual_collection"
ANSWER_TOP_K = 5
IMAGE_TEXT_TOP_K = 60
IMAGE_COLLECTION_TOP_K = 80
IMAGE_RESULTS_LIMIT = 20
TEXT_RANK_SCORE_WINDOW = 30


def get_collection_or_none(client, name):
    try:
        return client.get_collection(name=name)
    except Exception:
        return None


def open_rag_collections(client):
    text_collection = client.get_collection(name=TEXT_COLLECTION_NAME)
    image_collection = get_collection_or_none(client, IMAGE_COLLECTION_NAME)
    return text_collection, image_collection


def parse_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def distance_to_score(distance):
    if distance is None:
        return 0.0
    distance = max(0.0, to_float(distance))
    return 1.0 / (1.0 + distance)


def query_first(result, key):
    values = result.get(key) or [[]]
    return values[0] if values else []


def make_context(retrieved_docs, retrieved_metas):
    combined_context = ""
    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas), start=1):
        heading = meta.get("heading", "제목 없음")
        pages = meta.get("pages", "페이지 정보 없음")
        combined_context += f"[관련도 {i}순위 자료 | 출처: {heading} (페이지 {pages})]\n{doc}\n\n"
    return combined_context


def _candidate(candidates, file_name, image_path):
    resolved = resolve_image_path(image_path or file_name)
    key = resolved.name
    if key not in candidates:
        candidates[key] = {
            "name": key,
            "path": str(resolved),
            "heading": "제목 없음",
            "pages": "페이지 정보 없음",
            "page": "",
            "sources": [],
            "image_search_score": 0.0,
            "text_rank_score": 0.0,
            "page_score": 0.0,
            "mapping_score": 0.0,
            "siglip_score": 0.0,
            "score": 0.0,
        }
    return candidates[key]


@lru_cache(maxsize=1)
def load_image_page_index():
    images = parse_json(FINAL_PROCESSING_REPORT_PATH.read_text(encoding="utf-8"), [])
    by_page = {}
    for image in images:
        page = int(image.get("page", -1))
        if page < 0:
            continue
        by_page.setdefault(page, []).append(image)
    return by_page


def extract_pages(value):
    parsed = parse_json(value, None)
    if isinstance(parsed, list):
        return [int(page) for page in parsed if str(page).isdigit()]
    return [int(match) for match in re.findall(r"\d+", str(value or ""))]


def _add_text_image_candidates(candidates, metas):
    for rank, meta in enumerate(metas, start=1):
        rank_score = max(0.0, 1.0 - ((rank - 1) / max(1, TEXT_RANK_SCORE_WINDOW)))
        mapping_candidates = parse_json(meta.get("mapping_candidates"), [])
        mapping_by_name = {item.get("file_name"): item for item in mapping_candidates}

        for image_path in parse_json(meta.get("linked_images"), []):
            resolved = resolve_image_path(image_path)
            if not resolved.exists():
                continue

            mapping = mapping_by_name.get(resolved.name, {})
            item = _candidate(candidates, resolved.name, resolved)
            item["heading"] = meta.get("heading", item["heading"])
            item["pages"] = meta.get("pages", item["pages"])
            item["text_rank_score"] = max(item["text_rank_score"], rank_score)
            item["mapping_score"] = max(
                item["mapping_score"],
                to_float(mapping.get("hybrid_score"), to_float(meta.get("hybrid_mapping_score"))),
            )
            item["siglip_score"] = max(
                item["siglip_score"],
                to_float(mapping.get("image_text_similarity"), to_float(meta.get("image_text_similarity"))),
            )
            item["sources"].append(f"text_top_{rank}")


def _add_page_neighbor_candidates(candidates, metas):
    image_by_page = load_image_page_index()

    for rank, meta in enumerate(metas, start=1):
        rank_score = max(0.0, 1.0 - ((rank - 1) / max(1, TEXT_RANK_SCORE_WINDOW)))
        pages = extract_pages(meta.get("pages"))
        if not pages:
            continue

        candidate_pages = sorted({page + gap for page in pages for gap in (-1, 0, 1) if page + gap > 0})
        for image_page in candidate_pages:
            for image in image_by_page.get(image_page, []):
                image_path = FINAL_IMAGES_DIR / image["file_name"]
                if not image_path.exists():
                    continue

                page_gap = min(abs(image_page - page) for page in pages)
                page_multiplier = 1.0 if page_gap == 0 else 0.82
                item = _candidate(candidates, image["file_name"], image_path)
                item["heading"] = meta.get("heading", item["heading"])
                item["pages"] = meta.get("pages", item["pages"])
                item["page"] = image_page
                item["page_score"] = max(item["page_score"], rank_score * page_multiplier)
                item["siglip_score"] = max(item["siglip_score"], to_float(image.get("siglip_score")))
                item["sources"].append(f"page_neighbor_{rank}")


def _add_image_collection_candidates(candidates, result):
    metas = query_first(result, "metadatas")
    distances = query_first(result, "distances")
    documents = query_first(result, "documents")

    for rank, meta in enumerate(metas, start=1):
        file_name = meta.get("file_name")
        if not file_name:
            continue

        distance = distances[rank - 1] if rank - 1 < len(distances) else None
        doc = documents[rank - 1] if rank - 1 < len(documents) else ""
        image_path = meta.get("image_path", file_name)
        resolved = resolve_image_path(image_path)
        if not resolved.exists():
            continue

        item = _candidate(candidates, file_name, resolved)
        headings = parse_json(meta.get("source_headings"), [])
        pages = parse_json(meta.get("source_pages"), [])
        item["heading"] = next((heading for heading in headings if heading), item["heading"])
        item["pages"] = str(pages) if pages else item["pages"]
        item["page"] = meta.get("page", item["page"])
        item["image_search_score"] = max(item["image_search_score"], distance_to_score(distance))
        item["siglip_score"] = max(item["siglip_score"], to_float(meta.get("diagram_siglip_score")))
        item["sources"].append(f"image_db_{rank}")
        item["document_preview"] = doc[:240]


def rank_image_candidates(candidates, limit=IMAGE_RESULTS_LIMIT):
    ranked = []
    for item in candidates.values():
        source_bonus = min(0.08, 0.02 * len(set(item["sources"])))
        score = (
            0.42 * item["image_search_score"]
            + 0.18 * item["text_rank_score"]
            + 0.28 * item["page_score"]
            + 0.09 * item["mapping_score"]
            + 0.03 * item["siglip_score"]
            + source_bonus
        )
        item["score"] = round(score, 4)
        item["rank"] = 0
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item["score"],
            item["image_search_score"],
            item["page_score"],
            item["text_rank_score"],
            item["mapping_score"],
        ),
        reverse=True,
    )

    for rank, item in enumerate(ranked[:limit], start=1):
        item["rank"] = rank
    return ranked[:limit]


def retrieve_multimodal(
    question,
    embedder,
    text_collection,
    image_collection=None,
    answer_top_k=ANSWER_TOP_K,
    image_text_top_k=IMAGE_TEXT_TOP_K,
    image_collection_top_k=IMAGE_COLLECTION_TOP_K,
    image_results_limit=IMAGE_RESULTS_LIMIT,
):
    query_embedding = embedder.encode(question).tolist()

    answer_result = text_collection.query(query_embeddings=[query_embedding], n_results=answer_top_k)
    answer_docs = query_first(answer_result, "documents")
    answer_metas = query_first(answer_result, "metadatas")

    image_text_result = text_collection.query(query_embeddings=[query_embedding], n_results=image_text_top_k)
    image_text_metas = query_first(image_text_result, "metadatas")

    candidates = {}
    _add_text_image_candidates(candidates, image_text_metas)
    _add_page_neighbor_candidates(candidates, image_text_metas)

    if image_collection is not None:
        image_result = image_collection.query(
            query_embeddings=[query_embedding],
            n_results=image_collection_top_k,
        )
        _add_image_collection_candidates(candidates, image_result)

    images = rank_image_candidates(candidates, limit=image_results_limit)
    return {
        "query_embedding": query_embedding,
        "answer_docs": answer_docs,
        "answer_metas": answer_metas,
        "context": make_context(answer_docs, answer_metas),
        "images": images,
        "image_collection_available": image_collection is not None,
    }
