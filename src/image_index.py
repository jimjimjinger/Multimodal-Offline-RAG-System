import json
import math
import re
from pathlib import Path

from chromadb.errors import NotFoundError

from paths import FINAL_IMAGES_DIR, project_relative


IMAGE_COLLECTION_NAME = "doosan_image_collection"
HNSW_CONFIGURATION = {"hnsw": {"sync_threshold": 100}}
IMAGE_CONTEXT_CHUNKS = 3
IMAGE_TEXT_MAX_CHARS = 180


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _chunk_pages(chunk):
    return [int(page) for page in chunk.get("pages", [])]


def _bbox_distance(chunk, image):
    image_page = int(image["page"])
    same_page_bboxes = [
        bbox["coord"]
        for bbox in chunk.get("bboxes", [])
        if int(bbox.get("page", image_page)) == image_page and "coord" in bbox
    ]

    if not same_page_bboxes:
        pages = _chunk_pages(chunk)
        if not pages:
            return 99999.0
        return min(abs(page - image_page) for page in pages) * 1000.0

    min_x = min(bbox[0] for bbox in same_page_bboxes)
    min_y = min(bbox[1] for bbox in same_page_bboxes)
    max_x = max(bbox[2] for bbox in same_page_bboxes)
    max_y = max(bbox[3] for bbox in same_page_bboxes)
    text_center_x = (min_x + max_x) / 2
    text_center_y = (min_y + max_y) / 2

    bbox = image.get("bbox", {})
    image_center_x = (bbox.get("x0", 0.0) + bbox.get("x1", 0.0)) / 2
    image_center_y = (bbox.get("y0", 0.0) + bbox.get("y1", 0.0)) / 2
    return math.hypot(text_center_x - image_center_x, text_center_y - image_center_y)


def _chunk_page_index(text_chunks):
    index = {}
    for chunk_id, chunk in enumerate(text_chunks):
        for page in _chunk_pages(chunk):
            index.setdefault(page, []).append((chunk_id, chunk))
    return index


def _related_chunks_for_image(image, chunk_page_index):
    image_page = int(image["page"])
    scored = []
    nearby_chunks = {}
    for page in range(image_page - 1, image_page + 2):
        for chunk_id, chunk in chunk_page_index.get(page, []):
            nearby_chunks[chunk_id] = chunk

    for chunk_id, chunk in nearby_chunks.items():
        pages = _chunk_pages(chunk)
        if not pages:
            continue

        page_gap = min(abs(page - image_page) for page in pages)
        if page_gap > 1:
            continue

        distance = _bbox_distance(chunk, image)
        score = (page_gap * 1000.0) + distance
        scored.append((score, chunk_id, chunk))

    scored.sort(key=lambda item: item[0])
    return scored[:IMAGE_CONTEXT_CHUNKS]


def _build_image_document(image, related_chunks):
    parts = []

    for _, _, chunk in related_chunks:
        heading = _clean_text(chunk.get("heading"))
        text = _clean_text(chunk.get("text"))[:IMAGE_TEXT_MAX_CHARS]
        parts.append(f"{heading}. {text}" if heading else text)

    return "\n".join(parts) or "technical robot diagram"


def build_image_search_collection(
    text_chunks,
    image_metadata,
    embedding_model,
    client,
    reset=True,
    collection_name=IMAGE_COLLECTION_NAME,
):
    if reset:
        try:
            client.delete_collection(name=collection_name)
        except NotFoundError:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        configuration=HNSW_CONFIGURATION,
    )

    ids = []
    documents = []
    metadatas = []
    chunk_page_index = _chunk_page_index(text_chunks)

    for image in image_metadata:
        image_path = FINAL_IMAGES_DIR / image["file_name"]
        if not image_path.exists():
            continue

        related_chunks = _related_chunks_for_image(image, chunk_page_index)
        document = _build_image_document(image, related_chunks)

        chunk_ids = [f"chunk_{chunk_id}" for _, chunk_id, _ in related_chunks]
        headings = [_clean_text(chunk.get("heading")) for _, _, chunk in related_chunks]
        pages = sorted({page for _, _, chunk in related_chunks for page in chunk.get("pages", [])})

        ids.append(f"image_{Path(image['file_name']).stem}")
        documents.append(document)
        metadatas.append(
            {
                "file_name": image["file_name"],
                "page": int(image["page"]),
                "image_path": project_relative(image_path),
                "diagram_siglip_score": float(image.get("siglip_score", 0.0)),
                "source_chunk_ids": json.dumps(chunk_ids, ensure_ascii=False),
                "source_headings": json.dumps(headings, ensure_ascii=False),
                "source_pages": json.dumps(pages, ensure_ascii=False),
            }
        )

    if not documents:
        return collection

    embeddings = embedding_model.encode(
        documents,
        batch_size=32,
        show_progress_bar=True,
    ).tolist()

    for start in range(0, len(ids), 50):
        end = start + 50
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )

    return collection
