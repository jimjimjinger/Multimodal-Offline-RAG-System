import csv
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from image_index import IMAGE_COLLECTION_NAME
from paths import FINAL_IMAGES_DIR, FINAL_PROCESSING_REPORT_PATH, STAGE_CONTEXT_MAP_PATH, resolve_image_path


TEXT_COLLECTION_NAME = "doosan_manual_collection"
ANSWER_TOP_K = 5
IMAGE_TEXT_TOP_K = 60
IMAGE_COLLECTION_TOP_K = 80
IMAGE_RESULTS_LIMIT = 10
TEXT_RANK_SCORE_WINDOW = 30
STAGE_CONTEXT_WEIGHT = 0.50
STAGE_PAGE_PRIOR_WEIGHT = 0.25
STAGE_BASE_RANK_WINDOW = 120
STAGE_TEXT_TOP_K = 30

IMAGE_SEARCH_WEIGHT = 0.25
TEXT_RANK_WEIGHT = 0.15
PAGE_PROXIMITY_WEIGHT = 0.50
MAPPING_WEIGHT = 0.05
DIAGRAM_CONFIDENCE_WEIGHT = 0.05


class ExactVectorCollection:
    """Query a Chroma collection by exhaustively comparing stored vectors."""

    def __init__(self, collection):
        records = collection.get(include=["embeddings", "documents", "metadatas"])
        embeddings = records.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            raise RuntimeError(f"{collection.name} 컬렉션에 저장된 임베딩이 없습니다.")

        ids = list(records.get("ids") or [])
        documents = list(records.get("documents") or [None] * len(ids))
        metadatas = list(records.get("metadatas") or [None] * len(ids))
        if not (len(ids) == len(documents) == len(metadatas) == len(embeddings)):
            raise RuntimeError(f"{collection.name} 컬렉션의 저장 데이터 길이가 일치하지 않습니다.")

        stable_order = sorted(range(len(ids)), key=lambda index: ids[index])
        self.name = collection.name
        self._collection = collection
        self._ids = np.asarray([ids[index] for index in stable_order], dtype=str)
        self._documents = [documents[index] for index in stable_order]
        self._metadatas = [metadatas[index] for index in stable_order]
        self._embeddings = np.asarray(
            [embeddings[index] for index in stable_order],
            dtype=np.float64,
        )

        configuration = getattr(collection, "configuration", {}) or {}
        hnsw_configuration = configuration.get("hnsw") or {}
        self._space = hnsw_configuration.get("space", "l2")
        self._embedding_norms = np.linalg.norm(self._embeddings, axis=1)

    def count(self):
        return len(self._ids)

    def get(self, *args, **kwargs):
        return self._collection.get(*args, **kwargs)

    def _distances(self, query_embedding):
        if self._space == "cosine":
            query_norm = np.linalg.norm(query_embedding)
            denominator = np.maximum(self._embedding_norms * query_norm, 1e-12)
            return 1.0 - ((self._embeddings @ query_embedding) / denominator)
        if self._space == "ip":
            return 1.0 - (self._embeddings @ query_embedding)

        differences = self._embeddings - query_embedding
        return np.einsum("ij,ij->i", differences, differences)

    def query(self, query_embeddings, n_results=10, include=None, **kwargs):
        if kwargs:
            unsupported = ", ".join(sorted(kwargs))
            raise ValueError(f"정확 검색에서 지원하지 않는 query 옵션입니다: {unsupported}")

        queries = np.asarray(query_embeddings, dtype=np.float64)
        if queries.ndim == 1:
            queries = queries.reshape(1, -1)
        if queries.ndim != 2 or queries.shape[1] != self._embeddings.shape[1]:
            raise ValueError(
                f"질의 임베딩 차원이 올바르지 않습니다: "
                f"{queries.shape} != (*, {self._embeddings.shape[1]})"
            )

        requested = set(include or ["metadatas", "documents", "distances"])
        limit = min(max(1, int(n_results)), self.count())
        result = {"ids": []}
        if "documents" in requested:
            result["documents"] = []
        if "metadatas" in requested:
            result["metadatas"] = []
        if "distances" in requested:
            result["distances"] = []
        if "embeddings" in requested:
            result["embeddings"] = []

        for query_embedding in queries:
            distances = self._distances(query_embedding)
            order = np.lexsort((self._ids, distances))[:limit]
            result["ids"].append(self._ids[order].tolist())
            if "documents" in requested:
                result["documents"].append([self._documents[index] for index in order])
            if "metadatas" in requested:
                result["metadatas"].append([self._metadatas[index] for index in order])
            if "distances" in requested:
                result["distances"].append(distances[order].astype(float).tolist())
            if "embeddings" in requested:
                result["embeddings"].append(self._embeddings[order].astype(float).tolist())

        return result


def get_collection_or_none(client, name):
    try:
        return client.get_collection(name=name)
    except Exception:
        return None


def open_rag_collections(client):
    text_collection = ExactVectorCollection(client.get_collection(name=TEXT_COLLECTION_NAME))
    raw_image_collection = get_collection_or_none(client, IMAGE_COLLECTION_NAME)
    image_collection = ExactVectorCollection(raw_image_collection) if raw_image_collection is not None else None
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
            "diagram_score": 0.0,
            "stage_page_score": 0.0,
            "stage_keyword_score": 0.0,
            "stage_section_score": 0.0,
            "stage_map_score": 0.0,
            "stage_score": 0.0,
            "base_score": 0.0,
            "score": 0.0,
            "stage_reason": "",
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


def _split_terms(value):
    terms = []
    for term in re.split(r"[,;/|]+", str(value or "")):
        term = term.lower().strip()
        if term and term not in terms:
            terms.append(term)
    return terms


def _parse_page_ranges(value):
    ranges = []
    for part in str(value or "").split(";"):
        part = part.strip()
        if not part:
            continue
        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if range_match:
            start, end = sorted((int(range_match.group(1)), int(range_match.group(2))))
            ranges.append((start, end))
            continue
        for page in re.findall(r"\d+", part):
            value = int(page)
            ranges.append((value, value))
    return ranges


def _pages_from_ranges(ranges):
    pages = set()
    for start, end in ranges:
        pages.update(range(start, end + 1))
    return pages


@lru_cache(maxsize=8)
def load_stage_context_map(map_path=None):
    map_path = Path(map_path) if map_path else STAGE_CONTEXT_MAP_PATH
    if not map_path.exists():
        return {}

    with map_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    context_map = {}
    for row in rows:
        stage = row.get("실습 단계", "").strip()
        if not stage:
            continue

        context_map[stage] = {
            "stage_id": row.get("stage_id", ""),
            "stage": stage,
            "text_ranges": _parse_page_ranges(row.get("텍스트 페이지 범위")),
            "image_ranges": _parse_page_ranges(row.get("이미지 페이지 범위")),
            "section_terms": _split_terms(row.get("섹션 키워드")),
            "content_terms": _split_terms(row.get("본문 키워드")),
            "action_terms": _split_terms(row.get("동작/질문 키워드")),
            "weight": to_float(row.get("가중치"), 1.0),
            "evidence": row.get("근거", ""),
        }
    return context_map


def _stage_context_for(stage_label, map_path=None):
    if not stage_label:
        return None

    context_map = load_stage_context_map(str(map_path) if map_path else None)
    stage_label = str(stage_label).strip()
    if stage_label in context_map:
        return context_map[stage_label]

    lower_stage = stage_label.lower()
    for stage, context in context_map.items():
        if stage.lower() == lower_stage:
            return context
    return None


def extract_pages(value):
    parsed = parse_json(value, None)
    if isinstance(parsed, list):
        return [int(page) for page in parsed if str(page).isdigit()]
    return [int(match) for match in re.findall(r"\d+", str(value or ""))]


def image_page_from_name(value):
    match = re.search(r"page_(\d+)_", str(value or ""))
    return int(match.group(1)) if match else None


def candidate_pages(item):
    pages = set()
    page_value = item.get("page")
    if str(page_value).isdigit():
        pages.add(int(page_value))
    pages.update(extract_pages(item.get("pages")))
    image_page = image_page_from_name(item.get("name"))
    if image_page:
        pages.add(image_page)
    return pages


def page_range_score(pages, ranges):
    if not pages or not ranges:
        return 0.0

    best = 0.0
    for page in pages:
        for start, end in ranges:
            if start <= page <= end:
                best = max(best, 1.0)
                continue
            gap = min(abs(page - start), abs(page - end))
            if gap == 1:
                best = max(best, 0.70)
            elif gap == 2:
                best = max(best, 0.45)
    return best


def term_match_score(terms, text, max_terms=8):
    if not terms:
        return 0.0, []

    text = str(text or "").lower()
    matched = []
    for term in terms:
        if term and term in text and term not in matched:
            matched.append(term)

    denominator = min(max_terms, len(terms))
    return min(1.0, len(matched) / max(1, denominator)), matched


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
                to_float(mapping.get("mapping_score"), to_float(meta.get("mapping_score"))),
            )
            item["diagram_score"] = max(
                item["diagram_score"],
                to_float(mapping.get("diagram_siglip_score"), to_float(meta.get("diagram_siglip_confidence"))),
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
                item["diagram_score"] = max(item["diagram_score"], to_float(image.get("siglip_score")))
                item["sources"].append(f"page_neighbor_{rank}")


def _add_image_collection_candidates(
    candidates,
    result,
    source_prefix="image_db",
    score_key="image_search_score",
):
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
        item[score_key] = max(item[score_key], distance_to_score(distance))
        item["diagram_score"] = max(item["diagram_score"], to_float(meta.get("diagram_siglip_score")))
        item["sources"].append(f"{source_prefix}_{rank}")
        item["document_preview"] = doc[:240]


def _candidate_stage_text(item):
    return " ".join(
        str(value or "")
        for value in [
            item.get("name"),
            item.get("heading"),
            item.get("pages"),
            item.get("page"),
            item.get("document_preview"),
        ]
    ).lower()


def _add_stage_map_page_candidates(candidates, stage_context):
    if not stage_context:
        return

    image_by_page = load_image_page_index()
    pages = _pages_from_ranges(stage_context["image_ranges"])
    for page in sorted(pages):
        for image in image_by_page.get(page, []):
            image_path = FINAL_IMAGES_DIR / image["file_name"]
            if not image_path.exists():
                continue

            item = _candidate(candidates, image["file_name"], image_path)
            item["page"] = page
            item["stage_page_score"] = max(item["stage_page_score"], 1.0)
            item["diagram_score"] = max(item["diagram_score"], to_float(image.get("siglip_score")))
            item["sources"].append("stage_map_page")


def _apply_stage_context(candidates, stage_label, stage_context=None):
    if not stage_context:
        return

    keyword_terms = stage_context["content_terms"] + stage_context["action_terms"]
    for item in candidates.values():
        candidate_text = _candidate_stage_text(item)
        pages = candidate_pages(item)
        page_score = page_range_score(pages, stage_context["image_ranges"])
        keyword_score, matched_keywords = term_match_score(keyword_terms, candidate_text)
        section_score, matched_sections = term_match_score(stage_context["section_terms"], candidate_text)

        map_score = (
            0.50 * page_score
            + 0.10 * keyword_score
            + 0.40 * section_score
        ) * stage_context["weight"]

        item["stage_page_score"] = max(item["stage_page_score"], page_score)
        item["stage_keyword_score"] = max(item["stage_keyword_score"], keyword_score)
        item["stage_section_score"] = max(item["stage_section_score"], section_score)
        item["stage_map_score"] = max(item["stage_map_score"], map_score)
        item["stage_score"] = item["stage_map_score"]

        reason_parts = []
        if page_score:
            reason_parts.append(f"page={page_score:.2f}")
        if matched_keywords:
            reason_parts.append("keyword=" + ",".join(matched_keywords[:4]))
        if matched_sections:
            reason_parts.append("section=" + ",".join(matched_sections[:3]))
        item["stage_reason"] = "; ".join(reason_parts)


def _base_image_score(item):
    return (
        IMAGE_SEARCH_WEIGHT * item["image_search_score"]
        + TEXT_RANK_WEIGHT * item["text_rank_score"]
        + PAGE_PROXIMITY_WEIGHT * item["page_score"]
        + MAPPING_WEIGHT * item["mapping_score"]
        + DIAGRAM_CONFIDENCE_WEIGHT * item["diagram_score"]
    )


def rank_image_candidates(candidates, limit=IMAGE_RESULTS_LIMIT, use_stage_context=False):
    candidate_items = list(candidates.values())
    for item in candidate_items:
        base_score = _base_image_score(item)
        item["base_score"] = round(base_score, 4)
        item["base_rank"] = 0

    base_ranked = sorted(
        candidate_items,
        key=lambda item: (
            item["base_score"],
            item["image_search_score"],
            item["page_score"],
            item["text_rank_score"],
            item["mapping_score"],
        ),
        reverse=True,
    )
    for base_rank, item in enumerate(base_ranked, start=1):
        item["base_rank"] = base_rank

    ranked = []
    for item in candidate_items:
        if use_stage_context:
            if item["base_rank"] <= STAGE_BASE_RANK_WINDOW:
                rank_factor = 1.0 - ((item["base_rank"] - 1) / max(1, STAGE_BASE_RANK_WINDOW))
            elif item["stage_page_score"] > 0:
                rank_factor = 0.35
            else:
                rank_factor = 0.0
            score = (
                item["base_score"]
                + (STAGE_CONTEXT_WEIGHT * item["stage_score"] * rank_factor)
                + (STAGE_PAGE_PRIOR_WEIGHT * item["stage_page_score"])
            )
        else:
            score = item["base_score"]
        item["score"] = round(score, 4)
        item["rank"] = 0
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item["score"],
            item["stage_score"] if use_stage_context else 0.0,
            item["stage_page_score"] if use_stage_context else 0.0,
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


def _text_stage_score(doc, meta, stage_context):
    if not stage_context:
        return 0.0, ""

    pages = set(extract_pages(meta.get("pages")))
    text = " ".join(
        str(value or "")
        for value in [
            meta.get("heading"),
            meta.get("pages"),
            doc,
        ]
    ).lower()
    page_score = page_range_score(pages, stage_context["text_ranges"])
    keyword_score, matched_keywords = term_match_score(
        stage_context["content_terms"] + stage_context["action_terms"],
        text,
    )
    section_score, matched_sections = term_match_score(stage_context["section_terms"], text)
    score = (
        0.55 * page_score
        + 0.30 * keyword_score
        + 0.15 * section_score
    ) * stage_context["weight"]

    reason_parts = []
    if page_score:
        reason_parts.append(f"page={page_score:.2f}")
    if matched_keywords:
        reason_parts.append("keyword=" + ",".join(matched_keywords[:4]))
    if matched_sections:
        reason_parts.append("section=" + ",".join(matched_sections[:3]))
    return score, "; ".join(reason_parts)


def rank_text_results(ids, docs, metas, limit, stage_context=None):
    if not stage_context:
        return ids[:limit], docs[:limit], metas[:limit]

    items = []
    total = max(1, len(docs))
    for rank, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), start=1):
        base_rank_score = 1.0 - ((rank - 1) / total)
        stage_score, stage_reason = _text_stage_score(doc, meta, stage_context)
        score = base_rank_score + (0.28 * stage_score)
        meta = dict(meta)
        meta["g4_stage_score"] = round(stage_score, 4)
        meta["g4_stage_reason"] = stage_reason
        meta["g4_base_rank"] = rank
        items.append(
            {
                "id": doc_id,
                "doc": doc,
                "meta": meta,
                "score": score,
                "stage_score": stage_score,
                "base_rank_score": base_rank_score,
            }
        )

    items.sort(
        key=lambda item: (
            item["score"],
            item["stage_score"],
            item["base_rank_score"],
        ),
        reverse=True,
    )
    items = items[:limit]
    return (
        [item["id"] for item in items],
        [item["doc"] for item in items],
        [item["meta"] for item in items],
    )


def retrieve_multimodal(
    question,
    embedder,
    text_collection,
    image_collection=None,
    answer_top_k=ANSWER_TOP_K,
    image_text_top_k=IMAGE_TEXT_TOP_K,
    image_collection_top_k=IMAGE_COLLECTION_TOP_K,
    image_results_limit=IMAGE_RESULTS_LIMIT,
    stage_label=None,
    stage_context_map_path=None,
):
    query_embedding = embedder.encode(question).tolist()

    stage_context = _stage_context_for(stage_label, map_path=stage_context_map_path)
    answer_query_top_k = max(answer_top_k, STAGE_TEXT_TOP_K) if stage_context else answer_top_k

    answer_result = text_collection.query(query_embeddings=[query_embedding], n_results=answer_query_top_k)
    answer_ids = query_first(answer_result, "ids")
    answer_docs = query_first(answer_result, "documents")
    answer_metas = query_first(answer_result, "metadatas")
    answer_ids, answer_docs, answer_metas = rank_text_results(
        answer_ids,
        answer_docs,
        answer_metas,
        answer_top_k,
        stage_context=stage_context,
    )

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

    use_stage_context = bool(stage_context)
    if use_stage_context:
        if stage_context:
            _add_stage_map_page_candidates(candidates, stage_context)

        _apply_stage_context(candidates, stage_label, stage_context=stage_context)

    images = rank_image_candidates(
        candidates,
        limit=image_results_limit,
        use_stage_context=use_stage_context,
    )
    return {
        "query_embedding": query_embedding,
        "answer_ids": answer_ids,
        "answer_docs": answer_docs,
        "answer_metas": answer_metas,
        "context": make_context(answer_docs, answer_metas),
        "images": images,
        "image_collection_available": image_collection is not None,
        "stage_context_used": use_stage_context,
        "stage_context_map_used": stage_context is not None,
        "stage_context": stage_context,
    }
