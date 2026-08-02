# `src/app_qwen.py` 상세 설명서

## 1. 파일 역할

Qwen 2.5 모델로 공통 Streamlit 앱을 실행하는 진입 파일이다.

이 파일에는 `def` 함수가 없다. `app_runtime.run_app()`을 import한 뒤 최상위 코드에서 즉시 호출한다.

## 2. 전달 설정

| 매개변수 | 값 |
|---|---|
| `model_id` | `qwen2.5:7b` |
| `model_label` | `Qwen 2.5 7B Q4` |
| `page_title` | `Doosan Robotics Smart RAG - Qwen` |

`model_id`는 Ollama API에 그대로 전달되므로 Ollama에 같은 이름의 모델이 설치되어 있어야 한다.

## 3. 실행 흐름

```text
streamlit run app_qwen.py
        `- run_app(qwen2.5:7b, ...)
               |- BGE-M3와 DB 로드
               |- G3/G4 검색
               |- Ollama qwen2.5:7b 호출
               `- 결과 화면 표시
```

## 4. 실행 명령

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_qwen.py
```

## 5. 수정 시 주의사항

모델 크기나 quantization tag가 바뀌면 `model_id`를 실제 `ollama list` 결과와 동일하게 수정해야 한다. 화면 표시명인 `model_label`만 바꾸어서는 실제 호출 모델이 바뀌지 않는다.

