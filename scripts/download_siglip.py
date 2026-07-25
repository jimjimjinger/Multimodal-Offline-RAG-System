import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paths import SIGLIP_MODEL_DIR, configure_model_cache  # noqa: E402


def main():
    model_name = "google/siglip-base-patch16-224"
    configure_model_cache(offline=False)

    from transformers import SiglipModel, SiglipProcessor

    SIGLIP_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("SigLIP 모델 다운로드를 시작합니다.")
    processor = SiglipProcessor.from_pretrained(model_name)
    model = SiglipModel.from_pretrained(model_name)
    model.config.text_config.bos_token_id = processor.tokenizer.bos_token_id
    model.config.text_config.eos_token_id = processor.tokenizer.eos_token_id
    model.config.text_config.pad_token_id = processor.tokenizer.pad_token_id
    processor.save_pretrained(str(SIGLIP_MODEL_DIR))
    model.save_pretrained(str(SIGLIP_MODEL_DIR))
    print(f"모델 저장 완료: {SIGLIP_MODEL_DIR.resolve()}")


if __name__ == "__main__":
    main()
