# `src/app_llama.py` 상세 설명서

## 1. 파일 역할

Llama 3.1 모델로 공통 Streamlit 앱을 실행하는 진입 파일이다.

이 파일에는 `def` 함수가 없다. `app_runtime.run_app()`을 import한 뒤 최상위 코드에서 즉시 호출한다.

## 2. 전달 설정

| 매개변수 | 값 |
|---|---|
| `model_id` | `llama3.1:8b` |
| `model_label` | `Llama 3.1 8B Q4` |
| `page_title` | `Doosan Robotics Smart RAG - Llama` |

## 3. 실행 흐름

```text
streamlit run app_llama.py
        `- run_app(llama3.1:8b, ...)
               |- 공통 검색 파이프라인
               |- Ollama llama3.1:8b 호출
               `- Llama 답변과 동일 검색 근거 표시
```

## 4. 실행 명령

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_llama.py
```

## 5. 수정 시 주의사항

`model_label`은 화면 설명이고 `model_id`가 실제 Ollama 호출 대상이다. 다른 Llama tag를 사용할 때는 `ollama list`에 표시되는 정확한 이름을 지정해야 한다.

