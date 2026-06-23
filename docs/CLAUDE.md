# 프로젝트 컨텍스트 — 두산로보틱스 멀티모달 RAG 연구

## 연구자 정보
- 이름: 이지민
- 소속: 건국대학교 정보통신대학원 인공지능학과 (재학 중)
- 학부: 인하대학교 환경공학과 졸업
- 상태: 취업 준비 중

## 연구 목적
두산로보틱스 협동로봇 매뉴얼 PDF를 읽어, **텍스트와 이미지를 함께 답변하는 멀티모달 RAG 시스템** 구축.
- 오프라인 + 제한된 환경에서도 동작 가능하도록 설계
- 모델 용량 최소화가 핵심 목표 중 하나

## 현재 기술 스택
| 구성 요소 | 사용 기술 |
|---|---|
| 텍스트 임베딩 | BAAI/bge-m3 (SentenceTransformers) |
| 벡터 DB | ChromaDB (로컬 PersistentClient) |
| LLM | Qwen2.5:1.5b / Gemma2:2b (Ollama, 완전 오프라인) |
| 이미지 필터 | SigLIP (`models/siglip_local/` 로컬 저장) |
| UI | Streamlit (`src/app.py`, `src/app_gemma.py`) |

## 파이프라인 구조
```
data/raw/*.pdf
  → src/unified_extractor.py   # 텍스트 + 이미지 추출
  → src/text_filter.py         # 텍스트 정제
  → scripts/download_siglip.py # SigLIP 로컬 저장
  → SigLIP 필터링              # 의미 없는 이미지 제거
  → data/processed/final_refined_data/ # 정제된 이미지 보관
  → src/embedding_text_image.py        # BGE-M3 임베딩 + 2D 공간거리 기반 텍스트↔이미지 매핑 → ChromaDB 저장
  → src/app.py 또는 src/app_gemma.py   # Streamlit UI (Top-5 검색 + 답변 + 이미지 렌더링)
```

## 주요 파일 목록
| 파일/폴더 | 설명 |
|---|---|
| `src/app.py`, `src/app_gemma.py` | Streamlit 앱 |
| `src/unified_extractor.py` | PDF에서 이미지 추출 및 SigLIP 필터링 |
| `src/embedding_text_image.py` | 임베딩 + ChromaDB 적재 |
| `src/text_filter.py` | 텍스트 정제 및 청킹 |
| `scripts/download_siglip.py` | SigLIP 모델 로컬 다운로드 |
| `data/processed/text_chunks.json` | 추출된 텍스트 청크 (총 600개) |
| `data/processed/final_processing_report.json` | SigLIP 필터링 결과 (이미지 메타데이터) |
| `data/vector_db/rag_db/` | ChromaDB 벡터 DB 저장 폴더 |
| `data/processed/final_refined_data/` | SigLIP 필터링 통과 이미지 |
| `models/siglip_local/` | SigLIP 모델 로컬 저장 |
| `data/evaluation/` | 평가용 데이터셋 |

## 핵심 설계 원칙
1. **완전 오프라인 동작**: 인터넷 없이도 실행 가능 (Ollama + 로컬 모델)
2. **경량화 우선**: 1.5B 수준 LLM, 로컬 임베딩, 최소 의존성
3. **멀티모달 응답**: 텍스트 답변 + 연관 기술 도식(이미지) 동시 제공
4. **정밀 매핑**: 2D 공간거리 + 캡션 키워드 규칙으로 텍스트-이미지 연결
