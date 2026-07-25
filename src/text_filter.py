import json
import re

import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from paths import A_SERIES_PDF, BGE_M3_MODEL_ID, TEXT_CHUNKS_PATH, configure_model_cache


def _physical_chunk(heading, texts, pages, bboxes, span_bbox_pairs):
    return {
        "heading": heading,
        "text": " ".join(texts),
        "pages": sorted(pages),
        "bboxes": list(bboxes),
        "span_bbox_pairs": list(span_bbox_pairs),
    }


def get_physical_chunks(pdf_path):
    """Extract page-bounded text chunks while preserving each span's BBox."""
    physical_chunks = []
    current_heading = "문서 시작"
    current_body_texts = []
    current_pages = set()
    current_bboxes = []
    current_span_bbox_pairs = []

    header_y, footer_y = 70, 780

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue

                        bbox = span["bbox"]
                        y0 = bbox[1]
                        if y0 < header_y or y0 > footer_y:
                            continue

                        bbox_record = {
                            "page": page_num,
                            "coord": [round(coord, 2) for coord in bbox],
                        }
                        is_heading = span["size"] > 14 or (
                            span["size"] > 12 and span["flags"] & 2**4
                        )
                        if is_heading:
                            if current_body_texts:
                                physical_chunks.append(
                                    _physical_chunk(
                                        current_heading,
                                        current_body_texts,
                                        current_pages,
                                        current_bboxes,
                                        current_span_bbox_pairs,
                                    )
                                )
                            current_heading = text
                            current_body_texts = []
                            current_pages = set()
                            current_bboxes = []
                            current_span_bbox_pairs = []
                            continue

                        current_body_texts.append(text)
                        current_pages.add(page_num)
                        current_bboxes.append(bbox_record)
                        current_span_bbox_pairs.append((text, bbox_record))

            # Keep chunks on one PDF page while carrying the heading forward.
            if current_body_texts:
                physical_chunks.append(
                    _physical_chunk(
                        current_heading,
                        current_body_texts,
                        current_pages,
                        current_bboxes,
                        current_span_bbox_pairs,
                    )
                )
                current_body_texts = []
                current_pages = set()
                current_bboxes = []
                current_span_bbox_pairs = []

    return physical_chunks


def sentence_records(chunk):
    """Split text while preserving the exact source spans for each sentence."""
    text = chunk["text"]
    span_ranges = []
    cursor = 0
    for span_text, bbox in chunk.get("span_bbox_pairs", []):
        start = cursor
        end = start + len(span_text)
        span_ranges.append((start, end, bbox))
        cursor = end + 1

    records = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+", text):
        end = match.start()
        if end > start:
            records.append((start, end))
        start = match.end()
    if start < len(text):
        records.append((start, len(text)))

    output = []
    for sentence_start, sentence_end in records:
        sentence = text[sentence_start:sentence_end].strip()
        if len(sentence) <= 5:
            continue
        bboxes = [
            bbox
            for span_start, span_end, bbox in span_ranges
            if span_end > sentence_start and span_start < sentence_end
        ]
        output.append(
            {
                "text": sentence,
                "bboxes": bboxes,
                "pages": sorted({bbox["page"] for bbox in bboxes}),
            }
        )
    return output


def semantic_chunking(physical_chunks, model, similarity_threshold=0.5):
    """Group adjacent sentences while retaining only their exact BBoxes."""
    semantic_chunks = []
    prepared_chunks = []
    all_sentences = []

    for chunk in physical_chunks:
        records = sentence_records(chunk)
        if not records:
            continue
        start_index = len(all_sentences)
        all_sentences.extend(record["text"] for record in records)
        prepared_chunks.append((chunk, records, start_index, len(all_sentences)))

    if not all_sentences:
        return semantic_chunks

    all_embeddings = model.encode(all_sentences)

    for chunk, records, start_index, end_index in prepared_chunks:
        sentences = [record["text"] for record in records]
        embeddings = all_embeddings[start_index:end_index]
        current_texts = [sentences[0]]
        current_bboxes = list(records[0]["bboxes"])
        current_pages = set(records[0]["pages"])

        for index in range(1, len(sentences)):
            similarity = cosine_similarity(
                [embeddings[index - 1]],
                [embeddings[index]],
            )[0][0]
            if similarity < similarity_threshold:
                semantic_chunks.append(
                    {
                        "heading": chunk["heading"],
                        "text": " ".join(current_texts),
                        "pages": sorted(current_pages),
                        "bboxes": current_bboxes,
                    }
                )
                current_texts = [sentences[index]]
                current_bboxes = list(records[index]["bboxes"])
                current_pages = set(records[index]["pages"])
            else:
                current_texts.append(sentences[index])
                current_bboxes.extend(records[index]["bboxes"])
                current_pages.update(records[index]["pages"])

        semantic_chunks.append(
            {
                "heading": chunk["heading"],
                "text": " ".join(current_texts),
                "pages": sorted(current_pages),
                "bboxes": current_bboxes,
            }
        )

    return semantic_chunks


def save_text_chunks(chunks, output_path=TEXT_CHUNKS_PATH):
    """Atomically save chunks so interruption does not corrupt existing data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)


def main():
    configure_model_cache()

    print("BGE-M3 모델을 로컬 캐시에서 불러오는 중입니다.")
    model = SentenceTransformer(BGE_M3_MODEL_ID, local_files_only=True)

    print("페이지별 텍스트와 BBox를 추출하는 중입니다.")
    physical_chunks = get_physical_chunks(A_SERIES_PDF)

    print("문장 의미 유사도에 따라 텍스트 청크를 구성하는 중입니다.")
    final_chunks = semantic_chunking(
        physical_chunks,
        model,
        similarity_threshold=0.4,
    )
    if not final_chunks:
        raise RuntimeError("PDF에서 저장할 텍스트 청크를 생성하지 못했습니다.")

    save_text_chunks(final_chunks)
    print(f"{TEXT_CHUNKS_PATH}에 {len(final_chunks)}개 청크를 저장했습니다.")


if __name__ == "__main__":
    main()
