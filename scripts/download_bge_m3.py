import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import BGE_M3_MODEL_ID, HF_CACHE_DIR, configure_model_cache  # noqa: E402


def main():
    configure_model_cache(offline=False)

    from sentence_transformers import SentenceTransformer

    print(f"BGE-M3 다운로드를 시작합니다: {BGE_M3_MODEL_ID}")
    SentenceTransformer(BGE_M3_MODEL_ID)
    print(f"BGE-M3 캐시 준비 완료: {HF_CACHE_DIR}")


if __name__ == "__main__":
    main()
