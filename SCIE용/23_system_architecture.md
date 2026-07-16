# 시스템 아키텍처

## 목적

본 문서는 협동 로봇 실습 가이드를 위한 상황 인지형 멀티모달 RAG 시스템의 전체 구조를 설명한다. 논문에서는 Method 또는 Proposed Framework 섹션의 기반 문서로 사용한다.

## 전체 구조

시스템은 크게 오프라인 전처리 단계, 검색 인덱싱 단계, 런타임 질의응답 단계, 평가 단계로 구성된다.

```text
협동 로봇 매뉴얼 PDF
        |
        v
텍스트/이미지 추출 및 정제
        |
        +-- 텍스트 chunk 생성
        +-- 이미지/도식 추출
        +-- 텍스트-이미지 매핑 정보 생성
        |
        v
임베딩 및 ChromaDB 인덱싱
        |
        +-- BGE-M3 텍스트 임베딩
        +-- 이미지 관련 검색 정보 저장
        +-- SigLIP 기반 텍스트-이미지 유사도 신호 저장
        |
        v
G1/G2/G3/G4 검색 모듈
        |
        +-- G1: 키워드 기반 검색
        +-- G2: 텍스트 기반 RAG
        +-- G3: 멀티모달 RAG
        +-- G4: 단계 추정 기반 상황 인지형 멀티모달 RAG
        |
        v
로컬 LLM 응답 생성
        |
        +-- Qwen 2.5 7B Q4
        +-- Gemma 2 9B Q4
        +-- Llama 3.1 8B Q4
        |
        v
검색 성능 및 응답 품질 평가
```

## 주요 구성 요소

| 구성 요소 | 역할 | 관련 파일/폴더 |
|---|---|---|
| 원본 매뉴얼 | 협동 로봇 실습 매뉴얼 입력 자료 | `data/raw/` |
| 텍스트 전처리 | PDF 텍스트 추출, chunk 생성, page/section 정보 저장 | `data/processed/text_chunks.json` |
| 이미지 전처리 | 매뉴얼 이미지/도식 추출 및 정리 | `data/processed/final_refined_data/` |
| 텍스트 임베딩 | BGE-M3 기반 텍스트 검색 벡터 생성 | `models/hf_cache/`, `data/vector_db/` |
| 이미지-텍스트 매핑 | 이미지 주변 텍스트, page 근접도, SigLIP 유사도 신호 활용 | `data/processed/text_image_mapping_report.json` |
| 벡터 DB | 텍스트 및 이미지 검색 인덱스 저장 | `data/vector_db/rag_db/` |
| 검색 런타임 | G2/G3/G4 검색 로직 수행 | `src/rag_search.py` |
| 단계 추정기 | 질문과 실습 단계 context profile의 의미 유사도를 비교해 G4 적용 단계 추정 | `src/stage_classifier.py` |
| 앱 런타임 | Streamlit 앱, Ollama LLM 호출 | `src/app_runtime.py` |
| 모델별 앱 | Qwen/Gemma/Llama 앱 진입점 | `src/app_qwen.py`, `src/app_gemma.py`, `src/app_llama.py` |
| 평가 스크립트 | G1/G2/G3/G4 검색 성능, 단계 추정, 응답 품질 평가 | `scripts/evaluate_scie_all_groups.py`, `scripts/evaluate_stage_classifier.py`, `scripts/evaluate_scie_g4_auto_retrieval.py`, `scripts/evaluate_response_quality.py` |

## 모델 역할

| 모델/도구 | 사용 위치 | 역할 |
|---|---|---|
| BGE-M3 | 전처리 및 런타임 검색 | 질문과 텍스트 chunk 간 semantic retrieval |
| SigLIP | 전처리/매핑 신호 | 텍스트와 이미지 간 similarity 신호 생성 |
| ChromaDB | 검색 인덱스 | 임베딩 기반 텍스트/이미지 후보 검색 |
| Ollama | 로컬 LLM 실행 | Qwen/Gemma/Llama 답변 생성 |
| Qwen 2.5 7B Q4 | 응답 생성 | 최종 비교 모델 중 가장 안정적인 응답 품질 |
| Gemma 2 9B Q4 | 응답 생성 | 비교용 로컬 LLM |
| Llama 3.1 8B Q4 | 응답 생성 | 비교용 로컬 LLM |

주의할 점은 CLIP은 관련 연구 배경으로만 언급하며, 현재 구현에는 직접 사용하지 않았다는 것이다. 본 시스템의 이미지-텍스트 유사도 신호는 SigLIP을 기준으로 한다.

## 런타임 흐름

사용자가 앱에서 질문을 입력하면 다음 순서로 동작한다.

1. 질문을 BGE-M3 임베딩으로 변환한다.
2. G4 조건에서는 질문과 실습 단계 context profile을 비교해 실습 단계를 추정한다.
3. 단계 추정 신뢰도가 낮거나 1위와 2위 후보가 애매하면 G4를 적용하지 않고 G3 방식으로 검색한다.
4. ChromaDB에서 관련 텍스트 chunk를 검색한다.
5. G3/G4 조건에서는 관련 이미지 후보도 함께 검색한다.
6. G3는 텍스트 검색, 이미지 검색, page proximity, 텍스트-이미지 매핑 점수를 결합한다.
7. G4는 실습 단계 context map을 이용해 후보 순위를 재조정한다.
8. Top-5 텍스트 근거와 Top-10 이미지 후보를 구성한다.
9. Ollama를 통해 로컬 LLM이 한국어 실습 안내 답변을 생성한다.

## 논문에서의 표현 방향

논문에서는 본 시스템을 단순 챗봇이 아니라 다음과 같이 정의한다.

> 협동 로봇 실습 매뉴얼의 텍스트, 이미지/도식, 실습 단계 정보를 결합하여 검색 후보를 구성하고, 상황 정보 기반 re-ranking을 통해 실습 질의에 적합한 자료를 제공하는 context-aware multimodal RAG framework

## 현재 한계

- G4는 질문 기반 단계 추정 오차가 발생할 수 있으므로, 낮은 신뢰도 질문은 G3로 fallback하도록 구성했다.
- 정답 실습 단계가 주어진 oracle-stage 결과는 실제 앱 성능으로 해석하지 않고 참고 상한 성능으로만 사용한다.
- G4는 page-level 및 section-level context에는 효과적이지만, 같은 page 안의 유사 이미지 구분은 아직 부족하다.
- 응답 품질 평가는 rubric 기반 1차 평가까지 수행했으며, 최종 논문에서는 수동 검토 또는 전문가 평가로 보완하는 것이 바람직하다.
- 8GB 이하 RAM 환경을 목표로 하지만, 현재 전체 정량 평가는 개발용 노트북 환경에서 수행되었다. 따라서 제한 자원 관련 내용은 시스템 설계 특징으로 설명하고, 검증 완료된 성능 벤치마크로 주장하지 않는다.
