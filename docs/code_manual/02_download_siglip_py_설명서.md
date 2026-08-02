# `scripts/download_siglip.py` 상세 설명서

## 1. 파일 역할

이 스크립트는 Hugging Face의 `google/siglip-base-patch16-224` 모델과 전처리기를 다운로드하여 `models/siglip_local`에 저장한다. 이미지 추출과 텍스트-이미지 매핑 코드는 이후 인터넷에 접속하지 않고 이 로컬 폴더를 사용한다.

이 파일에는 `def` 함수가 없으며, 실행 시 최상위 코드가 위에서 아래로 바로 수행된다.

## 2. 실행 전 경로 준비

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
```

스크립트가 `scripts` 폴더 안에 있으므로 프로젝트 루트와 `src` 폴더를 계산한다. `src`를 Python 모듈 검색 경로의 맨 앞에 넣은 뒤 `paths.py`에서 `SIGLIP_MODEL_DIR`를 가져온다.

## 3. 다운로드 대상

| 항목 | 값 |
|---|---|
| Hugging Face 모델 ID | `google/siglip-base-patch16-224` |
| 저장 폴더 | `models/siglip_local/` |
| processor 클래스 | `SiglipProcessor` |
| model 클래스 | `SiglipModel` |

`AutoProcessor`나 `AutoModel`을 사용하지 않고 SigLIP 전용 클래스를 명시적으로 사용한다.

## 4. 실행 순서

1. `local_dir.mkdir(parents=True, exist_ok=True)`로 모델 폴더를 만든다.
2. `SiglipProcessor.from_pretrained(model_name)`으로 processor를 내려받는다.
3. `SiglipModel.from_pretrained(model_name)`으로 모델 가중치를 내려받는다.
4. `save_pretrained()`로 processor와 모델을 같은 로컬 폴더에 저장한다.
5. 성공하면 저장된 절대 경로를 출력한다.

## 5. 예외 처리

다운로드 또는 저장 과정에서 예외가 발생하면 오류 내용을 출력한다. 추가로 `sentencepiece` 패키지 설치를 안내하지만, 모든 오류가 `sentencepiece` 부족 때문인 것은 아니다. 네트워크, 디스크 공간, Hugging Face 접속, 패키지 버전도 함께 확인해야 한다.

예외를 다시 발생시키지 않고 출력만 하므로, 자동화 스크립트에서 종료 코드만으로 실패를 판단할 때는 주의해야 한다.

## 6. 생성 결과

`models/siglip_local`에는 일반적으로 다음 유형의 파일이 저장된다.

- 모델 설정 파일
- processor와 tokenizer 설정
- 모델 가중치 파일
- special token 관련 파일

정확한 파일명은 설치된 Transformers 버전과 모델 저장 형식에 따라 달라질 수 있다.

## 7. 다른 코드와의 연결

```text
download_siglip.py
        `- models/siglip_local/
               |- unified_extractor.py: 도면 여부 판별
               `- embedding_text_image.py: 이미지-텍스트 의미 유사도 계산
```

## 8. 실행 명령

```powershell
.\.venv\Scripts\python.exe scripts\download_siglip.py
```

다운로드가 완료된 뒤에는 앱을 실행할 때 이 스크립트를 다시 실행할 필요가 없다.

