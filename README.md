# Multimodal Offline RAG System

두산로보틱스 협동로봇 매뉴얼 PDF를 대상으로, 텍스트 검색 결과와 관련 도면 이미지를 함께 제공하는 오프라인 멀티모달 RAG 연구 프로젝트입니다.  
로컬 환경에서 BGE-M3, ChromaDB, SigLIP, Ollama 기반 LLM을 결합하여 질의응답을 수행합니다.

## 시스템 구조

```text
PDF 매뉴얼
-> 텍스트 및 이미지 추출
-> 텍스트 의미 단위 chunking
-> SigLIP 기반 도면 이미지 필터링
-> bbox 기반 텍스트-이미지 매핑
-> BGE-M3 텍스트 임베딩 생성
-> ChromaDB 벡터 DB 저장
-> Streamlit 질의응답 UI
-> Ollama 로컬 LLM 답변 생성
```

## 폴더 구조

```text
src/                  Python 파이프라인 및 앱 코드
scripts/              설치 및 유틸리티 스크립트
data/raw/             원본 PDF 매뉴얼
data/processed/       텍스트 chunk, 이미지 metadata, 추출 이미지
data/evaluation/      평가용 CSV/XLSX 파일
data/vector_db/       ChromaDB 벡터 DB
docs/                 연구 메모 및 프로젝트 문서
models/               로컬 모델 파일, Git 제외
runtime/              로컬 Ollama 실행 파일, Git 제외
```

## GitHub 업로드 기준

이 저장소에는 소스 코드, PDF 매뉴얼, 전처리 결과, 평가 파일, 현재 ChromaDB 데이터베이스가 포함되어 있습니다.

다음 항목은 용량이 크거나 개인 실행 환경에 해당하므로 GitHub에 포함하지 않습니다.

```text
.venv/
.python/
models/siglip_local/
models/hf_cache/
runtime/ollama/
runtime/ollama_home/
runtime/ollama_models/
runtime/downloads/
```

따라서 다른 컴퓨터에서 실행하려면 Python 패키지, SigLIP/BGE-M3 모델 캐시, Ollama, 로컬 LLM 모델을 다시 설치하거나 다운로드해야 합니다.

## 전처리 실행 순서

```powershell
.\.venv\Scripts\python.exe src\unified_extractor.py
.\.venv\Scripts\python.exe src\text_filter.py
.\.venv\Scripts\python.exe src\embedding_text_image.py
```

SigLIP 모델이 로컬에 없으면 먼저 다음 스크립트를 실행합니다.

```powershell
.\.venv\Scripts\python.exe scripts\download_siglip.py
```

## 앱 실행

먼저 Ollama를 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start_ollama.ps1
```

Streamlit 앱 실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app.py
```

Gemma 버전 실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```

## 현재 사용 모델

```text
텍스트 임베딩 모델: BAAI/bge-m3
이미지 필터링 모델: google/siglip-base-patch16-224
로컬 LLM: qwen2.5:1.5b / gemma2:2b (Ollama 기반)
```

## 향후 개선 방향

```text
1. 전처리 단계에서 SigLIP image-text similarity를 추가하여 텍스트-이미지 매핑 정확도 개선
2. 1.5B~2B급 소형 로컬 LLM과 4-bit 양자화 7B~8B급 중규모 로컬 LLM 비교
3. 텍스트-이미지 매핑 정확도, Top-k 검색 성능, LLM 답변 품질을 기준으로 평가
```
