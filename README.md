# Multimodal Offline RAG System

두산로보틱스 협동로봇 매뉴얼 PDF를 대상으로, 텍스트 검색 결과와 관련 도면 이미지를 함께 제공하는 오프라인 멀티모달 RAG 연구 프로젝트입니다.  
로컬 환경에서 BGE-M3, ChromaDB, SigLIP, Ollama 기반 LLM을 결합하여 질의응답을 수행합니다.

## 시스템 구조

```text
PDF 매뉴얼
-> 텍스트 및 이미지 추출
-> 텍스트 의미 단위 chunking
-> SigLIP 기반 도면 이미지 필터링
-> bbox + SigLIP similarity 기반 텍스트-이미지 매핑
-> BGE-M3 텍스트 임베딩 및 이미지 주변 문맥 임베딩 생성
-> ChromaDB 텍스트 컬렉션 + 이미지 전용 컬렉션 저장
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

Qwen 앱 실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_qwen.py
```

Gemma 앱 실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```

Llama 앱 실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_llama.py
```

## 현재 사용 모델

```text
텍스트 임베딩 모델: BAAI/bge-m3
이미지 필터링 모델: google/siglip-base-patch16-224
로컬 LLM: qwen2.5:7b / gemma2:9b / llama3.1:8b (Ollama 기반 4-bit 양자화 모델)
```

## 검색 방식

```text
답변 생성: 텍스트 컬렉션 Top-5 검색 결과를 LLM 컨텍스트로 사용
이미지 검색: 텍스트 컬렉션 Top-60 + 이미지 전용 컬렉션 Top-80 후보를 통합
이미지 출력: 통합 점수 기준 Top-10 도면 표시
통합 점수: 이미지 검색 점수 + 텍스트 검색 순위 + 페이지 근접도 + 전처리 SigLIP 매핑 점수
```

## 최근 평가 결과

```text
평가셋: data/evaluation/testset.xlsx, 38문항
Qwen 2.5 7B Q4: O 21 / △ 12 / X 5
Gemma 2 9B Q4: O 23 / △ 10 / X 5
Llama 3.1 8B Q4: O 19 / △ 13 / X 6
상세 결과: data/evaluation/model_eval_report.md
```

## 향후 개선 방향

```text
1. 정답 이미지가 Top-10 밖에 남는 실패 문항의 페이지/도면 단위 원인 분석
2. Qwen 2.5 7B, Gemma 2 9B, Llama 3.1 8B의 4-bit 양자화 모델 정밀 비교
3. 텍스트 답변 정확도, 이미지 Recall@K, 최종 멀티모달 정답률을 분리 평가
```
