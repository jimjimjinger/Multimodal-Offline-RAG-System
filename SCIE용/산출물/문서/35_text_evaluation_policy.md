# 텍스트 검색 평가 기준 정책

## 목적

이 문서는 텍스트 검색 성능 평가에서 strict 기준과 relaxed 기준을 어떻게 구분할지 정리한다. 현재 G1/G2/G3/G4 검색 성능표의 Text Recall@k는 relaxed 기준으로 산출되었으므로, 논문에서는 이 사실을 명확히 설명해야 한다.

## 현재 사용한 기준

현재 텍스트 검색 평가는 relaxed 기준을 사용하였다. 즉, 검색된 텍스트 후보가 정답 텍스트와 완전히 동일한 문장을 포함하지 않더라도 다음 조건 중 하나를 만족하면 정답으로 인정하였다.

| 인정 조건 | 설명 |
|---|---|
| page 일치 | 정답 텍스트가 포함된 매뉴얼 page와 검색 후보 page가 일치하거나 강하게 겹침 |
| 핵심 keyword 포함 | 정답 텍스트의 핵심 용어, 수치, 메뉴명, 기능명이 검색 후보에 포함됨 |
| 의미 유사성 | 표현은 다르지만 같은 절차, 설정, 안전 조건을 설명함 |

이 기준은 협동 로봇 매뉴얼의 특성상 하나의 정답이 여러 chunk 또는 인접 page에 걸쳐 나타날 수 있기 때문에 사용하였다.

## Strict 기준

Strict 기준은 다음과 같이 정의할 수 있다.

| 기준 | 설명 |
|---|---|
| exact text match | 검색 후보가 정답 텍스트 문장 또는 거의 동일한 문장을 포함해야 함 |
| exact page match | 정답 page와 검색 후보 page가 정확히 일치해야 함 |
| no semantic relaxation | 의미가 비슷해도 정답 문장 또는 page가 맞지 않으면 오답 처리 |

Strict 기준은 객관성은 높지만, 매뉴얼 chunk 분할 방식과 page 중복 문제에 민감하다. 따라서 현재 데이터셋에서는 strict 기준만 사용하면 실제로 필요한 정보를 검색했음에도 오답으로 계산될 가능성이 있다.

## 논문에서 사용할 권장 방식

본 연구에서는 다음 방식이 적절하다.

1. 메인 검색 성능표에는 현재 산출된 relaxed Text Recall@k를 사용한다.
2. 평가 지표 설명에서 relaxed 기준을 명확히 정의한다.
3. 이미지 검색은 정답 이미지 파일명 기반 exact match로 평가했다고 구분한다.
4. strict 텍스트 평가는 후속 보조 분석 또는 부록 후보로 남긴다.

## 논문 문장 초안

> Text retrieval was evaluated using a relaxed relevance criterion because relevant procedural information in the manual may appear across adjacent chunks or pages. A retrieved text candidate was considered correct if it matched the ground-truth page, contained key terms from the reference answer, or conveyed semantically equivalent procedural information. In contrast, image retrieval was evaluated using exact filename matching of the ground-truth image.

## 결과 해석 시 주의점

| 항목 | 해석 |
|---|---|
| Text Recall@k | relaxed 기준이므로 정보 검색 성공률에 가까움 |
| Image Recall@k | exact image filename 기준이므로 더 엄격함 |
| Both@k | relaxed text hit와 exact image hit가 동시에 만족된 비율 |
| Text MRR | 정답 또는 관련 텍스트가 얼마나 앞쪽에 배치되는지 평가 |
| Image MRR | 정답 이미지 파일이 얼마나 앞쪽에 배치되는지 평가 |

## 최종 판단

현재 논문에서는 relaxed text evaluation을 메인 기준으로 사용하되, 이를 명확히 기술한다. strict 기준은 현재 필수로 추가하지 않는다. 이유는 본 연구의 핵심 기여가 이미지/도식 검색과 context-aware re-ranking이며, 텍스트 검색은 이미 G2/G3/G4에서 Recall@5와 Recall@10이 충분히 높게 나타났기 때문이다.

추후 심사 과정에서 텍스트 평가 기준에 대한 지적이 있을 경우, strict 기준을 보조 실험으로 추가할 수 있다.
