from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EVALUATION_DATA_DIR = DATA_DIR / "evaluation"
VECTOR_DB_DIR = DATA_DIR / "vector_db" / "rag_db"

MODELS_DIR = PROJECT_ROOT / "models"
SIGLIP_MODEL_DIR = MODELS_DIR / "siglip_local"
HF_CACHE_DIR = MODELS_DIR / "hf_cache"
BGE_M3_MODEL_ID = "BAAI/bge-m3"

FINAL_IMAGES_DIR = PROCESSED_DATA_DIR / "final_refined_data"
TEXT_CHUNKS_PATH = PROCESSED_DATA_DIR / "text_chunks.json"
FINAL_PROCESSING_REPORT_PATH = PROCESSED_DATA_DIR / "final_processing_report.json"
PROCESSING_REPORT_PATH = PROCESSED_DATA_DIR / "processing_report.json"
TEXT_IMAGE_MAPPING_REPORT_PATH = PROCESSED_DATA_DIR / "text_image_mapping_report.json"

SCIE_DIR = PROJECT_ROOT / "SCIE용"
SCIE_DATA_DIR = SCIE_DIR / "data"
SCIE_EXCEL_DIR = SCIE_DIR / "excel"
STAGE_CONTEXT_MAP_PATH = SCIE_DATA_DIR / "09_stage_context_map.csv"
STAGE_CONTEXT_MAP_MANUAL_PATH = SCIE_DATA_DIR / "11_stage_context_map_manual.csv"

A_SERIES_PDF = RAW_DATA_DIR / "A-Series.pdf"


def configure_model_cache(offline=True):
    os.environ["HF_HOME"] = str(HF_CACHE_DIR)
    os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE_DIR / "transformers")
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    else:
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)


def project_relative(path):
    return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()


def resolve_image_path(image_path):
    path = Path(image_path)
    candidates = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend([
            PROJECT_ROOT / path,
            PROCESSED_DATA_DIR / path,
            FINAL_IMAGES_DIR / path.name,
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else path
