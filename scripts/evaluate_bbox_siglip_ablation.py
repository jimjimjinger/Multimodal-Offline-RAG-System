import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import FINAL_IMAGES_DIR, SCIE_DATA_DIR, VECTOR_DB_DIR, configure_model_cache  # noqa: E402
from rag_search import (  # noqa: E402
    IMAGE_COLLECTION_TOP_K,
    IMAGE_RESULTS_LIMIT,
    IMAGE_TEXT_TOP_K,
    open_rag_collections,
    retrieve_multimodal,
)


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "32_bbox_siglip_ablation_details.csv"
SUMMARY_OUTPUT_PATH = SCIE_DATA_DIR / "32_bbox_siglip_ablation_summary.csv"


class BBoxMappingCollection:
    """Expose BBox-ranked linked images without changing the stored collection."""

    def __init__(self, collection):
        self.collection = collection
        self.name = collection.name

    def query(self, *args, **kwargs):
        result = deepcopy(self.collection.query(*args, **kwargs))
        for metadata_group in result.get("metadatas") or []:
            for metadata in metadata_group:
                candidates = json.loads(metadata.get("mapping_candidates") or "[]")
                for candidate in candidates:
                    candidate["mapping_score"] = float(candidate.get("distance_score") or 0.0)

                spatial_candidates = [
                    candidate
                    for candidate in candidates
                    if candidate.get("spatial_candidate")
                ]
                spatial_candidates.sort(
                    key=lambda candidate: (
                        float(candidate.get("distance_score") or 0.0),
                        -float(candidate.get("distance") or 9999.0),
                        candidate.get("file_name") or "",
                    ),
                    reverse=True,
                )
                selected = spatial_candidates[:2]
                metadata["linked_images"] = json.dumps(
                    [str(FINAL_IMAGES_DIR / candidate["file_name"]) for candidate in selected],
                    ensure_ascii=False,
                )
                metadata["mapping_candidates"] = json.dumps(candidates, ensure_ascii=False)
                metadata["mapping_score"] = max(
                    (float(candidate.get("distance_score") or 0.0) for candidate in selected),
                    default=0.0,
                )
                metadata["mapping_method"] = "bbox_distance_ranking_ablation"
        return result


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def image_rank(expected_image, images):
    for rank, image in enumerate(images[:10], start=1):
        if image.get("name") == expected_image:
            return rank
    return None


def summarize(ranks):
    total = len(ranks)
    return {
        "query_count": total,
        "image_recall_at_1": sum(rank == 1 for rank in ranks) / total,
        "image_recall_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / total,
        "image_recall_at_10": sum(rank is not None and rank <= 10 for rank in ranks) / total,
        "image_mrr": sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / total,
    }


def percent(value):
    return f"{100 * value:.1f}%"


def main():
    configure_model_cache()
    questions = read_questions()
    embedder = SentenceTransformer("BAAI/bge-m3", local_files_only=True)
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)
    bbox_collection = BBoxMappingCollection(text_collection)

    rows = []
    bbox_ranks = []
    siglip_ranks = []
    for index, question in enumerate(questions, start=1):
        runs = {}
        for mode, collection in (
            ("bbox_mapping", bbox_collection),
            ("bbox_filter_siglip_ranking", text_collection),
        ):
            retrieval = retrieve_multimodal(
                question=question["질문"],
                embedder=embedder,
                text_collection=collection,
                image_collection=image_collection,
                answer_top_k=10,
                image_text_top_k=IMAGE_TEXT_TOP_K,
                image_collection_top_k=IMAGE_COLLECTION_TOP_K,
                image_results_limit=IMAGE_RESULTS_LIMIT,
            )
            rank = image_rank(question["정답 이미지"], retrieval["images"])
            runs[mode] = {
                "rank": rank,
                "top_10": [image["name"] for image in retrieval["images"][:10]],
            }

        bbox_ranks.append(runs["bbox_mapping"]["rank"])
        siglip_ranks.append(runs["bbox_filter_siglip_ranking"]["rank"])
        rows.append(
            {
                "질문 번호": question["질문 번호"],
                "질문": question["질문"],
                "정답 이미지": question["정답 이미지"],
                "BBox 기반 매핑 정답 순위": runs["bbox_mapping"]["rank"] or "",
                "BBox 기반 매핑 Top-10": "\n".join(runs["bbox_mapping"]["top_10"]),
                "BBox 필터 + SigLIP 정답 순위": runs["bbox_filter_siglip_ranking"]["rank"] or "",
                "BBox 필터 + SigLIP Top-10": "\n".join(runs["bbox_filter_siglip_ranking"]["top_10"]),
            }
        )
        print(
            f"[{index:02d}/{len(questions)}] {question['질문 번호']} "
            f"bbox={runs['bbox_mapping']['rank'] or '-'} "
            f"siglip={runs['bbox_filter_siglip_ranking']['rank'] or '-'}",
            flush=True,
        )

    DETAIL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DETAIL_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summaries = []
    for configuration, ranks, definition in (
        (
            "BBox-based mapping score",
            bbox_ranks,
            "Spatial candidates within the BBox gate are ranked by normalized BBox distance; top two links are retained.",
        ),
        (
            "BBox candidate filter + SigLIP ranking (final)",
            siglip_ranks,
            "BBox limits spatial candidates and stored SigLIP similarity ranks the retained text-image links.",
        ),
    ):
        metrics = summarize(ranks)
        summaries.append(
            {
                "configuration": configuration,
                "definition": definition,
                "query_count": metrics["query_count"],
                "Image Recall@1": percent(metrics["image_recall_at_1"]),
                "Image Recall@5": percent(metrics["image_recall_at_5"]),
                "Image Recall@10": percent(metrics["image_recall_at_10"]),
                "Image MRR": f"{metrics['image_mrr']:.3f}",
            }
        )

    with SUMMARY_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"summary: {SUMMARY_OUTPUT_PATH}")
    for summary in summaries:
        print(
            f"{summary['configuration']}: R@1={summary['Image Recall@1']} "
            f"R@5={summary['Image Recall@5']} R@10={summary['Image Recall@10']} "
            f"MRR={summary['Image MRR']}"
        )


if __name__ == "__main__":
    main()
