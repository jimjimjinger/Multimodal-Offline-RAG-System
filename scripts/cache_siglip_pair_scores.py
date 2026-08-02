import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import SiglipModel, SiglipProcessor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import (  # noqa: E402
    FINAL_IMAGES_DIR,
    FINAL_PROCESSING_REPORT_PATH,
    SCIE_DIR,
    SIGLIP_MODEL_DIR,
    TEXT_CHUNKS_PATH,
    configure_model_cache,
)


OUTPUT_DIR = SCIE_DIR / "weight_optimization"
OUTPUT_PATH = OUTPUT_DIR / "siglip_pair_scores.json"

TEXT_MAX_CHARS = 1200
IMAGE_BATCH_SIZE = 16
TEXT_BATCH_SIZE = 16
MAX_DISTANCE = 300.0
NEXT_PAGE_PENALTY = 1000.0
BELOW_TEXT_DISTANCE_FACTOR = 0.8
CAPTION_DISTANCE_FACTOR = 0.1


def extract_feature_tensor(features):
    if isinstance(features, torch.Tensor):
        return features
    if hasattr(features, "pooler_output"):
        return features.pooler_output
    if hasattr(features, "last_hidden_state"):
        return features.last_hidden_state[:, 0]
    raise TypeError(f"Unsupported SigLIP feature type: {type(features)}")


def batches(items, batch_size):
    for start in range(0, len(items), batch_size):
        yield start, items[start : start + batch_size]


def build_text_prompt(chunk):
    text = re.sub(r"\s+", " ", chunk.get("text", "")).strip()
    heading = re.sub(r"\s+", " ", chunk.get("heading", "")).strip()
    prompt = f"{heading}. {text}" if heading else text
    return prompt[:TEXT_MAX_CHARS]


def has_explicit_caption(text):
    return bool(re.search(r"(그림|도표|도식|Fig\.?|Figure)\s*\d+", text, re.IGNORECASE))


def bbox_distance(text_bboxes, image_bbox):
    if not text_bboxes:
        return 9999.0

    coords = [bbox.get("coord") for bbox in text_bboxes if bbox.get("coord")]
    if not coords:
        return 9999.0

    text_center_x = (min(coord[0] for coord in coords) + max(coord[2] for coord in coords)) / 2
    text_center_y = (min(coord[1] for coord in coords) + max(coord[3] for coord in coords)) / 2
    image_center_x = (image_bbox.get("x0", 0.0) + image_bbox.get("x1", 0.0)) / 2
    image_center_y = (image_bbox.get("y0", 0.0) + image_bbox.get("y1", 0.0)) / 2

    distance = math.hypot(text_center_x - image_center_x, text_center_y - image_center_y)
    if image_center_y > text_center_y:
        distance *= BELOW_TEXT_DISTANCE_FACTOR
    return distance


def distance_score(distance):
    if distance >= MAX_DISTANCE:
        return 0.0
    return max(0.0, 1.0 - (distance / MAX_DISTANCE))


def encode_images(images, processor, model, device):
    features = []
    for start, batch in batches(images, IMAGE_BATCH_SIZE):
        pil_images = []
        for image in batch:
            image_path = FINAL_IMAGES_DIR / image["file_name"]
            with Image.open(image_path) as source:
                pil_images.append(source.convert("RGB"))

        inputs = processor(images=pil_images, return_tensors="pt").to(device)
        with torch.inference_mode():
            batch_features = extract_feature_tensor(model.get_image_features(**inputs))
            batch_features = F.normalize(batch_features, p=2, dim=-1).cpu()
        features.append(batch_features)
        print(f"[SigLIP image] {min(start + len(batch), len(images))}/{len(images)}", flush=True)
    return torch.cat(features, dim=0)


def encode_texts(chunks, processor, model, device):
    prompts = [build_text_prompt(chunk) for chunk in chunks]
    features = []
    for start, batch in batches(prompts, TEXT_BATCH_SIZE):
        inputs = processor(
            text=batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
        ).to(device)
        with torch.inference_mode():
            batch_features = extract_feature_tensor(model.get_text_features(**inputs))
            batch_features = F.normalize(batch_features, p=2, dim=-1).cpu()
        features.append(batch_features)
        print(f"[SigLIP text] {min(start + len(batch), len(prompts))}/{len(prompts)}", flush=True)
    return torch.cat(features, dim=0)


def scalar_parameter(model, name, transform=None, default=0.0):
    value = getattr(model, name, None)
    if value is None:
        return float(default)
    value = value.detach().float().cpu()
    if transform:
        value = transform(value)
    return float(value.reshape(-1)[0])


def build_pair_records(chunks, images, cosine_matrix, logit_scale, logit_bias):
    images_by_page = {}
    for image_index, image in enumerate(images):
        images_by_page.setdefault(int(image["page"]), []).append((image_index, image))

    records = []
    pair_count = 0
    for chunk_index, chunk in enumerate(chunks):
        pages = chunk.get("pages") or []
        page = int(pages[0]) if pages else -1
        candidates = images_by_page.get(page, []) + images_by_page.get(page + 1, [])
        caption = has_explicit_caption(chunk.get("text", ""))

        candidate_rows = []
        candidate_logits = []
        for image_index, image in candidates:
            raw_distance = bbox_distance(chunk.get("bboxes", []), image.get("bbox", {}))
            adjusted_distance = raw_distance
            if int(image["page"]) == page + 1:
                adjusted_distance += NEXT_PAGE_PENALTY
            if caption:
                adjusted_distance *= CAPTION_DISTANCE_FACTOR

            cosine = float(cosine_matrix[chunk_index, image_index])
            logit = (cosine * logit_scale) + logit_bias
            probability = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, logit))))
            candidate_logits.append(logit)
            candidate_rows.append(
                {
                    "file_name": image["file_name"],
                    "page": int(image["page"]),
                    "raw_distance": round(raw_distance, 6),
                    "adjusted_distance": round(adjusted_distance, 6),
                    "distance_score": round(distance_score(adjusted_distance), 6),
                    "siglip_cosine": round(cosine, 8),
                    "siglip_cosine_01": round((cosine + 1.0) / 2.0, 8),
                    "siglip_logit": round(logit, 8),
                    "siglip_probability": round(probability, 10),
                    "diagram_confidence": float(image.get("siglip_score", 0.0)),
                }
            )

        if candidate_logits:
            logits = torch.tensor(candidate_logits, dtype=torch.float32)
            relative_scores = torch.softmax(logits, dim=0).tolist()
            for row, relative_score in zip(candidate_rows, relative_scores):
                row["siglip_relative_softmax"] = round(float(relative_score), 8)

        pair_count += len(candidate_rows)
        records.append(
            {
                "chunk_id": f"chunk_{chunk_index}",
                "page": page,
                "explicit_caption": caption,
                "pairs": candidate_rows,
            }
        )
        if (chunk_index + 1) % 100 == 0 or chunk_index + 1 == len(chunks):
            print(f"[pair cache] {chunk_index + 1}/{len(chunks)} chunks", flush=True)

    return records, pair_count


def main(force=False):
    configure_model_cache()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists() and not force:
        print(f"Cache already exists: {OUTPUT_PATH}")
        print("Use --force to rebuild it.")
        return

    chunks = json.loads(TEXT_CHUNKS_PATH.read_text(encoding="utf-8"))
    images = json.loads(FINAL_PROCESSING_REPORT_PATH.read_text(encoding="utf-8"))
    missing = [image["file_name"] for image in images if not (FINAL_IMAGES_DIR / image["file_name"]).exists()]
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} image files; first missing file: {missing[0]}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading SigLIP on {device}: {SIGLIP_MODEL_DIR}", flush=True)
    processor = SiglipProcessor.from_pretrained(str(SIGLIP_MODEL_DIR), local_files_only=True)
    model = SiglipModel.from_pretrained(str(SIGLIP_MODEL_DIR), local_files_only=True).to(device)
    model.eval()

    image_features = encode_images(images, processor, model, device)
    text_features = encode_texts(chunks, processor, model, device)
    cosine_matrix = text_features @ image_features.T
    logit_scale = scalar_parameter(model, "logit_scale", transform=torch.exp, default=1.0)
    logit_bias = scalar_parameter(model, "logit_bias", default=0.0)

    records, pair_count = build_pair_records(
        chunks,
        images,
        cosine_matrix,
        logit_scale,
        logit_bias,
    )
    output = {
        "metadata": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_path": str(SIGLIP_MODEL_DIR),
            "device": device,
            "text_count": len(chunks),
            "image_count": len(images),
            "pair_count": pair_count,
            "text_max_chars": TEXT_MAX_CHARS,
            "max_distance": MAX_DISTANCE,
            "next_page_penalty": NEXT_PAGE_PENALTY,
            "below_text_distance_factor": BELOW_TEXT_DISTANCE_FACTOR,
            "caption_distance_factor": CAPTION_DISTANCE_FACTOR,
            "logit_scale": logit_scale,
            "logit_bias": logit_bias,
        },
        "chunks": records,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created: {OUTPUT_PATH}")
    print(f"Cached pairs: {pair_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cache raw BBox and SigLIP pair scores for weight analysis.")
    parser.add_argument("--force", action="store_true", help="Rebuild an existing cache.")
    args = parser.parse_args()
    main(force=args.force)
