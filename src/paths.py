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

FINAL_IMAGES_DIR = PROCESSED_DATA_DIR / "final_refined_data"
TEXT_CHUNKS_PATH = PROCESSED_DATA_DIR / "text_chunks.json"
FINAL_PROCESSING_REPORT_PATH = PROCESSED_DATA_DIR / "final_processing_report.json"
PROCESSING_REPORT_PATH = PROCESSED_DATA_DIR / "processing_report.json"

A_SERIES_PDF = RAW_DATA_DIR / "A-Series.pdf"

RUNTIME_DIR = PROJECT_ROOT / "runtime"
OLLAMA_EXE = RUNTIME_DIR / "ollama" / "ollama.exe"
OLLAMA_HOME = RUNTIME_DIR / "ollama_home"
OLLAMA_MODELS = RUNTIME_DIR / "ollama_models"


def configure_model_cache():
    os.environ["HF_HOME"] = str(HF_CACHE_DIR)
    os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE_DIR / "transformers")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def ensure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


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
