# 실험 파이프라인

## 목적

본 문서는 G1, G2, G3, G4 비교군의 차이를 명확히 정리한다. 논문에서는 Experimental Setup 및 Ablation Study 설명에 활용한다.

## 비교군 개요

| 비교군 | 이름 | 핵심 목적 |
|---|---|---|
| G1 | Keyword Search | 키워드 기반 단순 검색 기준선 |
| G2 | Text-only RAG | 텍스트 임베딩 기반 RAG 성능 확인 |
| G3 | Multimodal RAG | 이미지/도식 정보를 추가했을 때의 검색 성능 확인 |
| G4 | Context-aware Multimodal RAG | 추정된 실습 단계 context를 추가했을 때의 실제 앱 조건 성능 확인 |

## G1: Keyword Search

G1은 질문과 텍스트 chunk 간 키워드 일치도를 기반으로 검색한다.

```text
질문
  -> 토큰화
  -> 텍스트 chunk와 키워드 일치도 계산
  -> Top-k 텍스트 후보 반환
```

G1은 이미지 검색을 수행하지 않으므로 Image Recall 및 Both@k는 계산하지 않는다.

## G2: Text-only RAG

G2는 BGE-M3 텍스트 임베딩을 이용하여 텍스트 chunk를 검색한다.

```text
질문
  -> BGE-M3 임베딩
  -> ChromaDB 텍스트 collection 검색
  -> Top-k 텍스트 후보 반환
  -> 로컬 LLM 답변 생성
```

G2는 텍스트 기반 RAG의 기준 성능을 제공한다. 이미지 후보는 사용하지 않는다.

## G3: Multimodal RAG

G3는 텍스트 검색 결과와 이미지 검색 결과를 함께 사용한다.

```text
질문
  -> BGE-M3 임베딩
  -> 텍스트 chunk 검색
  -> 이미지 후보 검색
  -> page proximity 계산
  -> 텍스트-이미지 매핑 점수 반영
  -> Top-k 텍스트 및 Top-k 이미지 후보 반환
  -> 로컬 LLM 답변 생성
```

G3의 핵심은 텍스트 근거뿐 아니라 이미지/도식 후보를 함께 제공한다는 점이다.

## G4: Context-aware Multimodal RAG

G4는 G3에 실습 단계 추정과 context map 기반 re-ranking을 추가한다.

```text
질문
  -> 실습 단계 context profile과 BGE-M3 유사도 비교
  -> 신뢰도가 충분하면 실습 단계 적용
  -> 신뢰도가 낮으면 G3 방식으로 fallback
  -> G3 검색 후보 생성
  -> 실습 단계 context map 조회
  -> page 범위 일치 점수 계산
  -> section/keyword 일치 점수 계산
  -> 텍스트 및 이미지 후보 re-ranking
  -> Top-k 텍스트 및 Top-k 이미지 후보 반환
  -> 로컬 LLM 답변 생성
```

G4 context map에는 정답 이미지 파일명이나 정답 chunk ID를 넣지 않는다. 실습 단계, page 범위, section heading, keyword만 사용한다.

정답 실습 단계 라벨을 알고 있다고 가정한 oracle-stage 평가는 실제 앱 조건이 아니므로 메인 비교군에서 제외한다. 필요한 경우 부록 또는 추가 분석에서 실습 단계 정보가 완전히 맞을 때의 상한 성능으로만 제시한다.

## 추가되는 요소 비교

| 요소 | G1 | G2 | G3 | G4 |
|---|---:|---:|---:|---:|
| 키워드 기반 텍스트 검색 | O | - | - | - |
| BGE-M3 텍스트 임베딩 검색 | - | O | O | O |
| 이미지 후보 검색 | - | - | O | O |
| page proximity | - | - | O | O |
| 텍스트-이미지 매핑 점수 | - | - | O | O |
| SigLIP similarity 신호 | - | - | O | O |
| 실습 단계 추정 | - | - | - | O |
| 실습 단계 context map | - | - | - | O |
| context-aware re-ranking | - | - | - | O |
| 로컬 LLM 답변 생성 | - | O | O | O |

## 최종 검색 성능 요약

| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 Keyword Search | 75.7% | 95.7% | 98.6% | 0.837 | - | - | - | - | - | - |
| G2 Text-only RAG | 81.4% | 95.7% | 100.0% | 0.879 | - | - | - | - | - | - |
| G3 Multimodal RAG | 81.4% | 95.7% | 100.0% | 0.879 | 32.9% | 70.0% | 75.7% | 0.485 | 70.0% | 75.7% |
| G4 Context-aware Multimodal RAG | 85.7% | 95.7% | 100.0% | 0.903 | 37.1% | 75.7% | 87.1% | 0.539 | 75.7% | 87.1% |

## 논문에서의 핵심 해석

- G1 대비 G2는 텍스트 검색의 Top-1 및 MRR을 개선한다.
- G3는 이미지 검색을 가능하게 하지만, Top-1 이미지 순위는 아직 낮다.
- G4는 질문 기반 단계 추정를 사용해 실제 앱 조건에서도 G3 대비 Image Recall@5, Image Recall@10, Image MRR을 개선한다.
- oracle-stage 결과는 메인 비교표에서 제외하고, 단계 정보가 정확할수록 개선 폭이 커질 수 있음을 보여주는 참고 분석으로만 사용한다.
