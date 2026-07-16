# G1/G2/G3/G4 검색 성능 비교 결과

## 비교군 정의

| 구분 | 비교군 | 설명 |
|---|---|---|
| G1 | 키워드 기반 단순 검색 | 질문과 매뉴얼 chunk의 단어 일치도를 사용한 baseline |
| G2 | 텍스트 기반 RAG | BGE-M3 텍스트 임베딩으로 텍스트 chunk만 검색 |
| G3 | 멀티모달 RAG | 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수 사용 |
| G4 | 상황 인지형 멀티모달 RAG | 질문에서 실습 단계를 추정한 뒤 G3 후보를 context map 기반으로 재순위화 |

## 전체 비교표

| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 키워드 기반 단순 검색 | 75.7% | 95.7% | 98.6% | 0.837 | - | - | - | - | - | - |
| G2 텍스트 기반 RAG | 81.4% | 95.7% | 100.0% | 0.879 | - | - | - | - | - | - |
| G3 멀티모달 RAG | 81.4% | 95.7% | 100.0% | 0.879 | 32.9% | 70.0% | 75.7% | 0.485 | 70.0% | 75.7% |
| G4 단계 추정 기반 상황 인지형 멀티모달 RAG | 85.7% | 95.7% | 100.0% | 0.903 | 37.1% | 75.7% | 87.1% | 0.539 | 75.7% | 87.1% |

평가 기준상 Text R@k와 Text MRR은 relaxed 기준으로 산출하였다. 정답 문장과 완전히 동일하지 않더라도 같은 page/section, 핵심 keyword, 의미 유사성이 충분하면 정답으로 인정하였다. 반면 Image R@k와 Image MRR은 strict filename matching 기준으로 산출하여, 정답 이미지 파일명이 Top-k 안에 포함된 경우만 정답으로 인정하였다. Both@k는 relaxed text hit와 strict image hit가 동시에 만족된 비율이다.

## 해석

- G1/G2는 이미지 검색을 수행하지 않기 때문에 Image Recall과 Both 지표는 산출하지 않았다.
- G2와 G3의 텍스트 검색 경로는 동일한 BGE-M3 텍스트 임베딩, 동일한 ChromaDB 텍스트 collection, 동일한 텍스트 chunk, 동일한 Top-k 검색 방식을 사용한다.
- 따라서 G2와 G3의 Text Recall@k 및 Text MRR이 동일한 것은 구현 오류가 아니라 실험 설계상 의도된 결과이다.
- G3는 텍스트 검색 성능을 높이기 위한 비교군이 아니라, G2의 텍스트 검색 결과에 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 추가해 이미지/도식 후보 검색 가능성을 확인하는 비교군이다.
- G4는 질문에서 실습 단계를 추정한 뒤, 실습 단계 문맥을 이용해 이미지 후보를 재순위화한 비교군이다.
- G4는 G3 대비 Image Recall@5가 70.0%에서 75.7%로, Image Recall@10이 75.7%에서 87.1%로, Image MRR이 0.485에서 0.539로 개선되었다.
- 다만 Image Recall@1은 37.1%로 여전히 낮으므로, G4의 성과는 이미지 검색 문제의 해결이 아니라 관련 이미지 후보의 Top-5/Top-10 포함률과 평균 순위 개선으로 해석한다.

## 산출 파일

- `SCIE용/data/15_g1_g2_g3_g4_retrieval_results.csv`
- `SCIE용/excel/15_g1_g2_g3_g4_retrieval_results.xlsx`
- `SCIE용/data/15_g1_g2_g3_g4_summary.csv`
- `SCIE용/excel/15_g1_g2_g3_g4_summary.xlsx`
