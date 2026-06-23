# Multimodal Offline RAG System

두산로보틱스 협동로봇 매뉴얼을 대상으로 텍스트 답변과 관련 도면 이미지를 함께 제공하는 오프라인 멀티모달 RAG 연구 프로젝트입니다.

## Folder Structure

```text
src/                  Python 실행 코드
data/raw/             원본 PDF 매뉴얼
data/processed/       텍스트 청크, 이미지 메타데이터, 정제 이미지
data/evaluation/      평가용 CSV/XLSX 데이터셋
data/vector_db/       ChromaDB 벡터 DB
models/               로컬 모델 및 Hugging Face 캐시
runtime/              Ollama 실행 파일, Ollama 모델, 설치 파일
docs/                 연구 메모와 프로젝트 문서
```

## Preprocessing

```powershell
.\.venv\Scripts\python.exe src\unified_extractor.py
.\.venv\Scripts\python.exe src\text_filter.py
.\.venv\Scripts\python.exe src\embedding_text_image.py
```

## Run App

```powershell
powershell -ExecutionPolicy Bypass -File .\start_ollama.ps1
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```
