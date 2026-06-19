import os
from transformers import SiglipProcessor, SiglipModel

# 1. 모델을 저장할 로컬 폴더
local_dir = "./siglip_local"
model_name = "google/siglip-base-patch16-224"

if not os.path.exists(local_dir):
    os.makedirs(local_dir)

print("모델 다운로드를 시작합니다. (명시적 클래스 사용)")

try:
    # AutoProcessor 대신 SiglipProcessor를 직접 사용합니다 (에러 방지)
    processor = SiglipProcessor.from_pretrained(model_name)
    model = SiglipModel.from_pretrained(model_name)

    # 로컬에 저장
    processor.save_pretrained(local_dir)
    model.save_pretrained(local_dir)
    
    print(f"✅ 성공! 모델 가중치가 '{os.path.abspath(local_dir)}'에 저장되었습니다.")

except Exception as e:
    print(f"❌ 에러 발생: {e}")
    print("\n💡 팁: 'pip install sentencepiece'를 터미널에 입력하고 다시 실행해보세요.")