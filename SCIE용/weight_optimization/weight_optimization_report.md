# 검색 가중치 최적화 결과

## 실험 원칙

- SigLIP 이미지와 텍스트 특징은 각각 한 번만 계산하고 이후 실험은 저장된 점수를 재정렬하는 방식으로 수행했다.
- 질문 또는 정답 이미지 파일명을 점수 계산 입력으로 사용하지 않았다. 정답 이미지는 검색 순위 평가에만 사용했다.
- 70개 질의를 5개 fold로 나누고, 각 fold를 제외한 질문에서 가중치를 선택한 뒤 제외한 fold에서 평가했다.
- 최적화 우선순위는 Image MRR, Image Recall@5, Image Recall@1, Image Recall@10 순서로 고정했다.
- 최종 배포용 값은 5-fold 검증 후 70개 전체에서 다시 선택한 탐색적 설정이다. 별도 외부 test set이 없으므로 확증적 최종 성능으로 과도하게 해석하면 안 된다.

## 기존 설정 재현과 교차검증 결과

| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| 기존 G3 재구성 | 41.4% | 72.9% | 80.0% | 0.537 |
| G3 비제약 탐색 5-fold | 44.3% | 75.7% | 80.0% | 0.559 |
| G3 제약 탐색 5-fold | 37.1% | 75.7% | 84.3% | 0.515 |
| G3 권장 반올림 설정(70개 탐색) | 38.6% | 75.7% | 84.3% | 0.534 |
| 기존 G4 재구성 | 44.3% | 85.7% | 91.4% | 0.594 |
| G4 고정 분류 임계값 5-fold | 44.3% | 87.1% | 92.9% | 0.607 |
| G4 권장 반올림 설정(70개 탐색) | 45.7% | 87.1% | 92.9% | 0.617 |

- G3 권장 설정 Image MRR 95% bootstrap CI: 0.443 - 0.625
- G4 권장 설정 Image MRR 95% bootstrap CI: 0.531 - 0.701
- 권장 G3-기존 G3 Image MRR 차이 95% bootstrap CI: -0.069 - +0.061
- 권장 G4-권장 G3 Image MRR 차이 95% bootstrap CI: +0.046 - +0.127

## BBox와 SigLIP 비율 비교

후보 수에 영향을 받지 않는 robust cosine 점수를 사용했다. 아래 표는 G3 나머지 가중치를 기존값으로 고정한 민감도 분석이다.

| BBox | SigLIP | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 1.0 | 34.3% | 77.1% | 87.1% | 0.521 |
| 0.1 | 0.9 | 38.6% | 77.1% | 85.7% | 0.546 |
| 0.2 | 0.8 | 37.1% | 78.6% | 84.3% | 0.543 |
| 0.3 | 0.7 | 35.7% | 78.6% | 84.3% | 0.531 |
| 0.4 | 0.6 | 38.6% | 77.1% | 82.9% | 0.538 |
| 0.5 | 0.5 | 38.6% | 75.7% | 82.9% | 0.537 |
| 0.6 | 0.4 | 38.6% | 75.7% | 82.9% | 0.531 |
| 0.7 | 0.3 | 40.0% | 75.7% | 80.0% | 0.532 |
| 0.8 | 0.2 | 38.6% | 75.7% | 80.0% | 0.524 |
| 0.9 | 0.1 | 38.6% | 75.7% | 81.4% | 0.525 |
| 1.0 | 0.0 | 37.1% | 72.9% | 81.4% | 0.515 |

## 선택된 G3 설정

- SigLIP 점수: `robust_cosine`
- BBox : SigLIP = 0.0 : 1.0
- BBox는 가중합 순위 점수보다 300-point 공간 후보 필터와 인접 페이지 제한에 사용한다.
- image search / text rank / page / mapping / diagram = 0.250 / 0.150 / 0.500 / 0.050 / 0.050
- source coefficient = 0.000

## G3 ablation

| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| Recommended G3 | 38.6% | 75.7% | 84.3% | 0.534 |
| without image_search | 38.6% | 75.7% | 84.3% | 0.535 |
| without text_rank | 38.6% | 80.0% | 82.9% | 0.542 |
| without page | 35.7% | 71.4% | 82.9% | 0.503 |
| without mapping | 40.0% | 75.7% | 85.7% | 0.545 |
| without diagram_confidence | 38.6% | 75.7% | 85.7% | 0.540 |
| without source bonus | 38.6% | 75.7% | 84.3% | 0.534 |
| BBox only mapping | 42.9% | 75.7% | 85.7% | 0.552 |
| SigLIP only mapping | 38.6% | 75.7% | 84.3% | 0.534 |

## 선택된 G4 설정

- 단계 적용 최소 score / margin = 0.45 / 0.03
- page / keyword / section = 0.500 / 0.100 / 0.400
- stage query scale / stage rank scale = 0.00 / 0.00
- context coefficient / page prior coefficient = 0.50 / 0.25
- base rank window = 120
- 자동 단계 Top-1 정확도 = 62/70 (88.6%)
- 권장 임계값 적용 질문 = 54/70 (77.1%)

## G4 ablation

| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| Recommended G4 | 45.7% | 87.1% | 92.9% | 0.617 |
| without stage evidence | 44.3% | 85.7% | 92.9% | 0.604 |
| without page prior | 45.7% | 87.1% | 92.9% | 0.614 |
| without stage image query | 45.7% | 87.1% | 92.9% | 0.617 |
| without stage rank | 45.7% | 87.1% | 92.9% | 0.617 |
| context map only | 45.7% | 87.1% | 92.9% | 0.617 |

## 텍스트 G4 가중치

텍스트 재정렬은 탐색값이 전체 70개에서는 소폭 높았지만 5-fold 검증에서 일관된 개선이 확인되지 않아 기존 설정을 유지한다.

- page / keyword / section = 0.550 / 0.300 / 0.150
- stage coefficient = 0.28

| 구성 | Text R@1 | Text R@5 | Text R@10 | Text MRR |
|---|---:|---:|---:|---:|
| 현재 텍스트 G4 | 84.3% | 95.7% | 100.0% | 0.894 |
| 텍스트 G4 5-fold 검증 | 84.3% | 97.1% | 100.0% | 0.895 |
| 텍스트 G4 전체 재선택 | 85.7% | 97.1% | 100.0% | 0.903 |

## 해석 제한

- 동일한 70개 질문 안에서 교차검증했으므로, 선택된 가중치를 논문의 확정값으로 사용하기 전 별도 외부 질문 세트 검증이 권장된다.
- 응답 생성 품질은 이번 탐색 대상이 아니다. 검색 가중치가 확정된 뒤 최종 설정에서만 LLM 응답을 다시 생성해야 한다.
- 가중치가 0에 가깝거나 제거했을 때 성능이 유지되는 구성요소는 단순화 후보이며, 무조건 시스템에서 삭제하기 전에 fold별 일관성을 확인해야 한다.

## 산출 파일

- `SCIE용/weight_optimization/best_weights.json`
- `SCIE용/weight_optimization/g3_search_top100.csv`
- `SCIE용/weight_optimization/g4_search_top100.csv`
- `SCIE용/weight_optimization/best_question_ranks.csv`
