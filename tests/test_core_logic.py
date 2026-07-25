import io
import math
import sys
import unittest
from pathlib import Path

import chromadb
import numpy as np
import torch
from chromadb.errors import NotFoundError
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from embedding_text_image import (  # noqa: E402
    COLLECTION_NAME,
    IMAGE_BACKUP_COLLECTION_NAME,
    IMAGE_COLLECTION_NAME,
    IMAGE_STAGING_COLLECTION_NAME,
    TEXT_BACKUP_COLLECTION_NAME,
    TEXT_STAGING_COLLECTION_NAME,
    _promote_collection_pair,
    calculate_2d_distance,
    check_explicit_caption,
)
from rag_search import rank_image_candidates, retrieve_multimodal  # noqa: E402
from stage_classifier import classify_stage  # noqa: E402
from text_filter import semantic_chunking, sentence_records  # noqa: E402
from unified_extractor import (  # noqa: E402
    classify_siglip_scores,
    is_blank_or_solid_image,
)
from evaluate_scie_retrieval import clean_csv_rows  # noqa: E402


class FakeEmbeddingModel:
    def __init__(self, values):
        self.values = values

    def encode(self, _texts):
        return np.asarray(self.values, dtype=float)


class FakeQueryEmbedder:
    def encode(self, _text):
        return np.asarray([1.0, 0.0], dtype=float)


class FakeCollection:
    def __init__(self):
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }


class CoreLogicTests(unittest.TestCase):
    def test_blank_white_image_is_rejected(self):
        image = Image.new("RGB", (200, 200), "white")
        payload = io.BytesIO()
        image.save(payload, format="PNG")

        self.assertTrue(is_blank_or_solid_image(payload.getvalue()))

    def test_fully_transparent_image_is_rejected(self):
        image = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
        payload = io.BytesIO()
        image.save(payload, format="PNG")

        self.assertTrue(is_blank_or_solid_image(payload.getvalue()))

    def test_corrupt_image_is_rejected(self):
        self.assertTrue(is_blank_or_solid_image(b"not-an-image"))

    def test_siglip_filter_compares_relative_pair_scores(self):
        accepted = classify_siglip_scores(torch.tensor([0.20, 0.35]))
        rejected = classify_siglip_scores(torch.tensor([0.40, 0.30]))

        self.assertTrue(accepted["accepted"])
        self.assertFalse(rejected["accepted"])

    def test_sentence_bbox_mapping_uses_source_offsets(self):
        chunk = {
            "text": "첫 문장입니다. 둘째 문장입니다.",
            "span_bbox_pairs": [
                ("첫", {"page": 1, "coord": [0, 0, 1, 1]}),
                ("문장입니다.", {"page": 1, "coord": [1, 0, 2, 1]}),
                ("둘째", {"page": 1, "coord": [0, 2, 1, 3]}),
                ("문장입니다.", {"page": 1, "coord": [1, 2, 2, 3]}),
            ],
        }

        records = sentence_records(chunk)

        self.assertEqual(2, len(records))
        self.assertEqual(2, len(records[0]["bboxes"]))
        self.assertEqual([0, 2, 1, 3], records[1]["bboxes"][0]["coord"])

    def test_semantic_chunking_never_falls_back_to_unrelated_pages(self):
        chunk = {
            "heading": "시험",
            "text": "첫 문장입니다. 둘째 문장입니다.",
            "pages": [1],
            "bboxes": [
                {"page": 1, "coord": [0, 0, 1, 1]},
                {"page": 1, "coord": [1, 0, 2, 1]},
                {"page": 1, "coord": [0, 2, 1, 3]},
                {"page": 1, "coord": [1, 2, 2, 3]},
            ],
            "span_bbox_pairs": [
                ("첫", {"page": 1, "coord": [0, 0, 1, 1]}),
                ("문장입니다.", {"page": 1, "coord": [1, 0, 2, 1]}),
                ("둘째", {"page": 1, "coord": [0, 2, 1, 3]}),
                ("문장입니다.", {"page": 1, "coord": [1, 2, 2, 3]}),
            ],
        }
        model = FakeEmbeddingModel([[1.0, 0.0], [0.0, 1.0]])

        chunks = semantic_chunking([chunk], model, similarity_threshold=0.5)

        self.assertEqual(2, len(chunks))
        self.assertTrue(all(result["pages"] == [1] for result in chunks))
        self.assertTrue(all(len(result["bboxes"]) == 2 for result in chunks))

    def test_bbox_distance_uses_only_the_image_page(self):
        text_bboxes = [
            {"page": 1, "coord": [0, 0, 10, 10]},
            {"page": 2, "coord": [100, 100, 110, 110]},
        ]
        image_bbox = {"x0": 100, "y0": 100, "x1": 110, "y1": 110}

        distance = calculate_2d_distance(text_bboxes, image_bbox, image_page=2)

        self.assertEqual(0.0, distance)

    def test_korean_figure_caption_is_detected(self):
        self.assertTrue(check_explicit_caption("그림 12의 배선 방법을 확인한다."))
        self.assertTrue(check_explicit_caption("도면 3을 참고한다."))
        self.assertFalse(check_explicit_caption("배선 방법을 확인한다."))

    def test_stage_threshold_uses_unrounded_margin(self):
        second_score = 0.47004
        profiles = [
            {"stage": "A", "stage_id": "A"},
            {"stage": "B", "stage_id": "B"},
        ]
        profile_embeddings = [
            np.asarray([0.5, math.sqrt(1 - 0.5**2)]),
            np.asarray([second_score, math.sqrt(1 - second_score**2)]),
        ]

        result = classify_stage(
            question="질문",
            embedder=FakeQueryEmbedder(),
            profiles=profiles,
            profile_embeddings=profile_embeddings,
            min_score=0.4,
            min_margin=0.03,
        )

        self.assertFalse(result["used"])
        self.assertEqual(0.03, result["margin"])

    def test_image_ranking_uses_unrounded_base_score(self):
        def candidate(page_score, image_score):
            return {
                "image_search_score": image_score,
                "text_rank_score": 0.0,
                "page_score": page_score,
                "mapping_score": 0.0,
                "diagram_score": 0.0,
                "stage_score": 0.0,
                "stage_page_score": 0.0,
            }

        candidates = {
            "raw_winner": candidate(1.0, 0.0),
            "rounded_tie_winner": candidate(0.4998, 1.0),
        }

        ranked = rank_image_candidates(candidates, limit=2)

        self.assertEqual(candidates["raw_winner"], ranked[0])

    def test_multimodal_retrieval_queries_text_collection_once(self):
        collection = FakeCollection()

        result = retrieve_multimodal(
            question="질문",
            embedder=FakeQueryEmbedder(),
            text_collection=collection,
            image_collection=None,
        )

        self.assertEqual(1, len(collection.calls))
        self.assertEqual([], result["answer_docs"])

    def test_staging_collections_replace_old_pair(self):
        client = chromadb.EphemeralClient()
        old_text = client.get_or_create_collection(COLLECTION_NAME)
        old_text.add(ids=["old_text"], documents=["old"], embeddings=[[1.0, 0.0]])
        old_image = client.get_or_create_collection(IMAGE_COLLECTION_NAME)
        old_image.add(ids=["old_image"], documents=["old"], embeddings=[[1.0, 0.0]])
        staging_text = client.get_or_create_collection(TEXT_STAGING_COLLECTION_NAME)
        staging_text.add(ids=["new_text"], documents=["new"], embeddings=[[0.0, 1.0]])
        staging_image = client.get_or_create_collection(IMAGE_STAGING_COLLECTION_NAME)
        staging_image.add(ids=["new_image"], documents=["new"], embeddings=[[0.0, 1.0]])

        _promote_collection_pair(client)

        self.assertEqual(
            ["new_text"],
            client.get_collection(COLLECTION_NAME).get()["ids"],
        )
        self.assertEqual(
            ["new_image"],
            client.get_collection(IMAGE_COLLECTION_NAME).get()["ids"],
        )
        collection_names = {collection.name for collection in client.list_collections()}
        self.assertNotIn(TEXT_BACKUP_COLLECTION_NAME, collection_names)
        self.assertNotIn(IMAGE_BACKUP_COLLECTION_NAME, collection_names)

    def test_collection_pair_promotion_validates_both_staging_collections_first(self):
        client = chromadb.EphemeralClient()
        old_text = client.get_or_create_collection(COLLECTION_NAME)
        old_text.add(ids=["old_text"], documents=["old"], embeddings=[[1.0, 0.0]])
        old_image = client.get_or_create_collection(IMAGE_COLLECTION_NAME)
        old_image.add(ids=["old_image"], documents=["old"], embeddings=[[1.0, 0.0]])
        client.get_or_create_collection(TEXT_STAGING_COLLECTION_NAME)

        with self.assertRaises(NotFoundError):
            _promote_collection_pair(client)

        self.assertEqual(
            ["old_text"],
            client.get_collection(COLLECTION_NAME).get()["ids"],
        )
        self.assertEqual(
            ["old_image"],
            client.get_collection(IMAGE_COLLECTION_NAME).get()["ids"],
        )

    def test_csv_detail_lines_do_not_keep_trailing_whitespace(self):
        rows = [{"details": "first | \nsecond   \n", "rank": 1}]

        cleaned = clean_csv_rows(rows)

        self.assertEqual("first |\nsecond", cleaned[0]["details"])
        self.assertEqual(1, cleaned[0]["rank"])


if __name__ == "__main__":
    unittest.main()
