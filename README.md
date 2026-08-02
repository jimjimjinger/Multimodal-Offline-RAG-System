# Multimodal Offline RAG System

협동 로봇 실습 매뉴얼을 대상으로, 사용자의 질문에 맞는 **텍스트 설명**과 **관련 이미지/도식**을 함께 찾아서 로컬 LLM으로 답변하는 오프라인 멀티모달 RAG 연구 프로젝트입니다.

본 프로젝트의 핵심 목표는 단순한 챗봇 구현이나 답변 생성 품질 향상이 아니라, 협동 로봇 실습 환경에서 **텍스트 기반 RAG보다 멀티모달 RAG와 상황 정보가 검색 성능을 개선하는지**를 실험적으로 확인하는 것입니다.

## 한 줄 요약

사용자가 “로봇 베이스 고정 볼트 규격과 토크가 뭐야?”처럼 실습 질문을 하면, 시스템은 매뉴얼에서 관련 텍스트 근거를 찾고, 해당 설명과 연결된 그림/도식 후보를 함께 보여준 뒤, 로컬 LLM이 한국어 답변을 생성합니다.

## 연구 목적

협동 로봇 실습에서는 텍스트 설명만으로는 부족한 경우가 많습니다.

- 메뉴 경로는 텍스트로 설명되어 있지만 실제 화면 이미지를 봐야 이해되는 경우
- 배선, 접지, 설치, 안전 설정처럼 도식이 함께 필요한 경우
- 같은 단어가 여러 실습 단계에서 반복되어 검색 결과가 섞이는 경우

이 프로젝트는 이런 문제를 해결하기 위해 다음 정보를 함께 사용합니다.

```text
텍스트 설명
+ 이미지/도식
+ PDF page 위치
+ 텍스트-이미지 매핑 점수
+ 실습 단계 context
```

## 전체 구조

```text
PDF 매뉴얼
-> 텍스트와 이미지/도식 추출
-> 텍스트 chunk 생성
-> 이미지 page, 주변 텍스트, BBox 정보 연결
-> BBox 거리로 공간 후보 필터링
-> SigLIP 기반 텍스트-이미지 의미 순위 계산
-> BGE-M3 임베딩 생성
-> ChromaDB 텍스트/이미지 컬렉션 저장
-> G1/G2/G3/G4 검색 실험
-> Ollama 로컬 LLM 답변 생성
-> Streamlit 앱에서 텍스트 답변 + 관련 이미지 표시
```

## 비교군

논문 실험에서는 네 가지 검색 구조를 비교합니다.

| 비교군 | 이름 | 설명 |
|---|---|---|
| G1 | Keyword Search | 질문과 매뉴얼 텍스트의 단어 일치도를 사용한 기준선 |
| G2 | Text-only RAG | BGE-M3 임베딩으로 텍스트 chunk만 검색 |
| G3 | Multimodal RAG | 텍스트 검색, 이미지 검색, page proximity, 텍스트-이미지 매핑 점수 결합 |
| G4 | Context-aware Multimodal RAG | 질문에서 실습 단계를 추정하고 단계별 context map으로 후보를 재순위화 |

## 현재 핵심 결과

70개 실습 질의셋 기준 검색 성능입니다.

| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 Keyword Search | 75.7% | 95.7% | 98.6% | 0.837 | - | - | - | - | - | - |
| G2 Text-only RAG | 81.4% | 95.7% | 100.0% | 0.879 | - | - | - | - | - | - |
| G3 Multimodal RAG | 81.4% | 95.7% | 100.0% | 0.879 | 45.7% | 71.4% | 80.0% | 0.572 | 71.4% | 80.0% |
| G4 Context-aware Multimodal RAG | 85.7% | 95.7% | 100.0% | 0.903 | 48.6% | 77.1% | 87.1% | 0.620 | 77.1% | 87.1% |

현재 결과에서 가장 중요한 점은 다음입니다.

- 텍스트 검색은 이미 비교적 안정적입니다.
- G2와 G3는 동일한 BGE-M3 텍스트 검색 경로를 사용하므로 Text Recall@k와 Text MRR이 동일합니다.
- G3의 역할은 텍스트 검색 개선이 아니라, 이미지 전용 검색과 텍스트-이미지 매핑을 추가해 이미지/도식 후보를 함께 찾는 것입니다.
- 멀티모달 RAG의 병목은 이미지 검색 순위입니다.
- G4는 G3 대비 이미지 후보의 Top-5/Top-10 포함률과 평균 순위를 개선했습니다.
- 특히 Image Recall@5는 `71.4% -> 77.1%`, Image Recall@10은 `80.0% -> 87.1%`, Image MRR은 `0.572 -> 0.620`으로 개선되었습니다.
- 다만 Image Recall@1은 `48.6%`로 절반 미만이어서, 이미지 검색 문제를 완전히 해결한 것은 아닙니다.

BBox는 최종 점수에 직접 더하지 않습니다. 전처리에서 공간적으로 가까운 이미지를 후보로 남기는 필터로 사용하고, 후보 순위는 SigLIP 의미 유사도로 결정합니다. G3/G4 가중치는 70개 질의 기반 탐색과 5-fold 내부 검증으로 선택했으므로, 현재 결과는 내부 파일럿 성능이며 별도 hold-out 데이터 검증이 필요합니다.

평가 기준은 텍스트와 이미지가 다릅니다. Text Recall@k와 Text MRR은 relaxed 기준으로, 같은 page/section, 핵심 keyword, 의미 유사성이 충분하면 정답으로 인정했습니다. Image Recall@k와 Image MRR은 strict filename matching 기준으로, 정답 이미지 파일명이 Top-k 안에 포함된 경우만 정답으로 인정했습니다. Both@k는 relaxed text hit와 strict image hit가 동시에 만족된 비율입니다.

## 응답 품질 평가

검색 성능과 별도로, Qwen/Gemma/Llama 로컬 LLM 답변 품질도 평가했습니다.

- 전체 응답 수: 630개
- 비교 조건: G2/G3/G4 x Qwen/Gemma/Llama x 70개 질문
- 평가 기준: 정확성, 구체성, 실습 단계 적합성, 안전성, 이해 용이성
- 전체 630개는 rubric 기반 1차 평가
- G4 오류 및 애매 사례 54개는 연구자 수동 검토

현재 해석은 다음과 같습니다.

```text
G4는 이미지 검색 순위를 개선했지만,
생성 응답 품질이 모든 모델에서 일관되게 상승한 것은 아닙니다.
따라서 본 연구의 핵심 기여는 응답 생성 자체가 아니라
context-aware multimodal retrieval, 특히 이미지/도식 검색 순위 개선에 있습니다.
```

## 오프라인 및 제한 자원 목표

이 시스템은 외부 API 없이 로컬에서 동작하는 것을 목표로 합니다.

- 벡터 DB: ChromaDB 로컬 저장
- 임베딩: BGE-M3
- 이미지-텍스트 유사도: SigLIP, 전처리 단계에서 계산
- 로컬 LLM: Ollama 기반 Qwen/Gemma/Llama
- 모델 구성: 7B~9B급 Q4 양자화 모델

8GB RAM급 제한 환경에서 활용 가능한 구조를 목표로 하지만, 현재 정량 실험은 개발용 노트북에서 수행했습니다. 따라서 이 항목은 검증 완료된 최소 사양이 아니라 시스템 설계 특징이며, 8GB 이하 장비에서의 속도와 메모리 사용량은 후속 검증 항목입니다.

## 주요 폴더

```text
src/                  앱 및 검색 런타임 코드
scripts/              평가, 전처리, 다운로드, 실험 스크립트
docs/code_manual/     전처리부터 앱 실행까지 Python 파일별 상세 설명서
data/raw/             원본 PDF 매뉴얼
data/processed/       추출 텍스트, 이미지, 최종 정제 데이터
data/vector_db/       ChromaDB 벡터 DB
SCIE용/               논문, 실험 데이터, Excel, 도식, Markdown 백업 ZIP
SCIE용/산출물/        교수님 보고 및 논문 작성용 핵심 산출물 모음
models/               로컬 모델 파일, Git 제외
runtime/              Ollama 실행 환경, Git 제외
```

## 코드 상세 설명서

전체 실행 순서와 파일별 함수 설명은 아래 문서에서 확인할 수 있습니다.

| 용도 | 파일 |
|---|---|
| 전체 파이프라인과 실행 순서 | `docs/code_manual/00_전체_실행_순서.md` |
| Python 파일별 상세 설명 | `docs/code_manual/01_paths_py_설명서.md` ~ `12_app_llama_py_설명서.md` |
| 이전 Markdown 문서 전체 백업 | `SCIE용/현재까지_MD_전체.zip` |
| IEEE Access 영문 통합 원고 | `SCIE용/논문/IEEE Access 영문 통합 원고.docx` |
| 국문 원문 초안 | `SCIE용/논문/원문 초안.docx` |
| 논문용 핵심 산출물 | `SCIE용/산출물/` |

## 실행 방법

### 1. Ollama 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\start_ollama.ps1
```

### 2. Qwen 앱 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_qwen.py
```

### 3. Gemma 앱 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```

### 4. Llama 앱 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_llama.py
```

## 전처리 실행 순서

처음부터 데이터베이스를 다시 만들 때 사용합니다.

```powershell
.\.venv\Scripts\python.exe src\unified_extractor.py
.\.venv\Scripts\python.exe src\text_filter.py
.\.venv\Scripts\python.exe src\embedding_text_image.py
```

SigLIP 모델이 로컬에 없으면 먼저 다운로드합니다.

```powershell
.\.venv\Scripts\python.exe scripts\download_siglip.py
```

## 현재 사용 모델

```text
텍스트 임베딩: BAAI/bge-m3
이미지-텍스트 유사도: google/siglip-base-patch16-224
로컬 LLM: qwen2.5:7b / gemma2:9b / llama3.1:8b
LLM 실행 방식: Ollama 기반 Q4 양자화 모델
```

## 논문 방향

현재 논문 방향은 다음 문장으로 요약할 수 있습니다.

```text
협동 로봇 실습 매뉴얼처럼 텍스트, 이미지, 실습 단계 정보가 함께 필요한 환경에서
context-aware multimodal RAG가 text-only RAG 및 일반 multimodal RAG보다
검색 성능, 특히 이미지 검색 순위를 개선할 수 있는지 검증한다.
```

현재 기여점은 다음과 같습니다.

1. 협동 로봇 실습 매뉴얼 기반 70개 질의셋 구축
2. 정답 텍스트, 정답 이미지, 실습 단계 라벨링
3. G1/G2/G3/G4 비교 실험 구조 정리
4. G4 context map 기반 re-ranking 구현
5. G3 대비 G4 이미지 검색 성능 개선 확인
6. 응답 품질 평가는 보조 분석으로 분리하고 G4 오류/애매 사례를 연구자 검토

## GitHub 업로드 기준

이 저장소에는 소스 코드, 전처리 결과, 평가 파일, 논문 산출물이 포함되어 있습니다.

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

다른 컴퓨터에서 실행하려면 Python 패키지, SigLIP/BGE-M3 모델 캐시, Ollama, 로컬 LLM 모델을 다시 설치해야 합니다.
