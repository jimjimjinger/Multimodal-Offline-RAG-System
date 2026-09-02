# 최종 논문 수치 근거 및 재현 경로

## 1. 적용 범위

이 문서는 IEEE Access 영문 통합 원고의 Table III, Table VI 및 G3-G4 paired bootstrap 결과가 어떤 원시 파일과 실행 스크립트에서 산출되었는지 기록한다. 논문에 보고하는 최종 수치는 아래의 **end-to-end 평가 결과**를 기준으로 한다.

`weight_optimization_report.md`에 기록된 값은 2026-07-24에 후보 feature cache로 수행한 **가중치 선택 단계의 내부 탐색 결과**이다. 해당 값은 가중치와 구조를 선택하기 위한 분석이며, 다음 날 현재 검색 파이프라인으로 다시 수행한 최종 end-to-end 평가 수치와 동일한 표로 해석하지 않는다.

## 2. Table VI: G1-G4 최종 검색 성능

- 질의별 원시 순위: `SCIE용/data/15_g1_g2_g3_g4_retrieval_results.csv`
- 요약 지표: `SCIE용/data/15_g1_g2_g3_g4_summary.csv`
- 질의 수: 70개
- 이미지 정답 기준: 정답 이미지 파일명의 strict match
- 텍스트 정답 기준: page/section 일치, 핵심 keyword 포함 또는 의미적 동등성 중 하나를 인정하는 relaxed relevance

| 비교군 | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| G3 | 45.7% | 71.4% | 80.0% | 0.572 |
| G4 | 48.6% | 77.1% | 87.1% | 0.620 |

`15_g1_g2_g3_g4_summary.csv`의 값은 질의별 순위 파일에서 Recall@k와 reciprocal rank를 다시 계산하여 확인하였다.

## 3. Table III: BBox와 SigLIP 매핑 비교

- 재현 스크립트: `scripts/evaluate_bbox_siglip_ablation.py`
- 질의별 원시 순위: `SCIE용/data/32_bbox_siglip_ablation_details.csv`
- 요약 지표: `SCIE용/data/32_bbox_siglip_ablation_summary.csv`
- 실행 조건: 동일한 70개 질의, 동일한 현재 벡터 DB, exhaustive vector search, 동일한 G3 검색 가중치
- DB 변경 여부: 없음. 평가 시 text metadata의 linked-image 선택과 mapping score만 메모리에서 교체

| 매핑 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| BBox 기반 매핑 점수 | 35.7% | 58.6% | 72.9% | 0.474 |
| BBox 후보 필터 + SigLIP 순위화 | 45.7% | 71.4% | 80.0% | 0.572 |

BBox 비교군은 300-point 공간 게이트를 통과한 후보를 정규화된 BBox 거리로 정렬하고 상위 두 이미지를 text-image link로 유지한다. 최종 방식은 BBox를 공간 후보 제한에만 사용하고, 저장된 SigLIP 유사도로 text-image link를 정렬한다. 최종 SigLIP 방식이 기존 G3 수치를 정확히 재현했으므로 Table III은 이 재현 결과를 사용한다.

## 4. G3-G4 paired bootstrap

- 실행 스크립트: `scripts/paired_bootstrap_retrieval.py`
- 결과 파일: `SCIE용/data/31_g3_g4_paired_bootstrap_ci.csv`
- 표본: 동일한 70개 질의의 G3-G4 paired rank
- 재표집 횟수: 200,000회
- 구간: percentile-based 95% confidence interval

| 지표 | G4-G3 차이 | 95% CI |
|---|---:|---:|
| Image Recall@1 | +2.9%p | -2.9%p ~ +8.6%p |
| Image Recall@5 | +5.7%p | 0.0%p ~ +12.9%p |
| Image Recall@10 | +7.1%p | +1.4%p ~ +14.3%p |
| Image MRR | +0.048 | +0.012 ~ +0.088 |

동일한 70개 질의를 가중치 선택과 최종 평가에 모두 사용했으므로 이 구간은 내부 질의셋에서의 paired uncertainty만 나타낸다. 독립 외부 데이터에 대한 일반화 또는 확증적 우월성의 근거로 해석하지 않는다.

## 5. 파일 무결성 기록

| 파일 | SHA-256 |
|---|---|
| `15_g1_g2_g3_g4_retrieval_results.csv` | `EE00C0946574763983A1FDCDAC1CB87F19BF529D4516AEDAF5CFC7F73E6A7DD9` |
| `15_g1_g2_g3_g4_summary.csv` | `6647C31FB15ACF400650480DABDB0D1D2AA93CB31BE237783C6FBEF5CBFB8AB6` |
| `31_g3_g4_paired_bootstrap_ci.csv` | `049692D9F938CE6CC8BDF332B724CD70993B00916B255823DED6D16270469B75` |
| `32_bbox_siglip_ablation_details.csv` | `AE83E13D490B34BF3568E03E4A07ED4BA38EDB3BDB0B7ED602A0F11429EC25FE` |
| `32_bbox_siglip_ablation_summary.csv` | `652412D5741AEA5EB012F4D59C66BBB325B9427060B29C960101F269ABF77351` |

## 6. 원고 재생성 시 검증

`scripts/build_ieee_access_docx.py`는 원고 생성 전에 다음 항목을 검사한다.

1. G3/G4 최종 이미지 지표가 `15_g1_g2_g3_g4_summary.csv`와 원고에서 일치하는지 확인한다.
2. Table III의 두 행이 `32_bbox_siglip_ablation_summary.csv`와 정확히 일치하는지 확인한다.
3. bootstrap 결과 파일이 네 지표와 70개 질의를 포함하는지 확인한다.

검사에 실패하면 DOCX 생성을 중단하여 과거 수치와 최신 수치가 섞이는 것을 방지한다.
