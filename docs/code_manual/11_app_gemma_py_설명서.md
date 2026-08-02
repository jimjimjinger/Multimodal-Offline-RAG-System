# `src/app_gemma.py` 상세 설명서

## 1. 파일 역할

Gemma 2 모델로 공통 Streamlit 앱을 실행하는 진입 파일이다.

이 파일에는 `def` 함수가 없다. `app_runtime.run_app()`을 import한 뒤 최상위 코드에서 즉시 호출한다.

## 2. 전달 설정

| 매개변수 | 값 |
|---|---|
| `model_id` | `gemma2:9b` |
| `model_label` | `Gemma 2 9B Q4` |
| `page_title` | `Doosan Robotics Smart RAG - Gemma` |

## 3. 실행 흐름

```text
streamlit run app_gemma.py
        `- run_app(gemma2:9b, ...)
               |- 공통 검색 파이프라인
               |- Ollama gemma2:9b 호출
               `- Gemma 답변과 동일 검색 근거 표시
```

세 앱은 같은 검색 DB와 같은 G3/G4 코드를 사용한다. 따라서 모델별 차이는 검색 후보가 아니라 검색 근거를 받아 생성한 답변에서 발생한다.

## 4. 실행 명령

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```

## 5. 수정 시 주의사항

Gemma의 실제 Ollama tag가 다르면 `model_id`도 함께 바꿔야 한다. 9B Q4 모델은 Qwen 7B보다 메모리 요구량이 클 수 있으므로 제한 환경에서는 실제 최대 RAM을 별도로 측정해야 한다.

