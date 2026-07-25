# 논문용 최종 정리본

## 1. 연구 방향

본 연구는 협동 로봇 실습 매뉴얼을 대상으로, 학습자의 실습 질의에 대해 텍스트 설명과 이미지/도식 자료를 함께 검색하는 상황 인지형 멀티모달 RAG 구조를 제안한다. 논문의 핵심 기여는 생성 응답 품질 향상이 아니라, 실습 단계 context를 활용해 이미지/도식 자료와 멀티모달 근거의 검색 순위를 개선하는 것이다. 또한 외부 API 없이 로컬 벡터 DB와 4-bit 양자화 LLM을 활용하여 오프라인 및 8GB RAM급 제한 환경에서 활용 가능한 구조를 목표로 한다. 다만 오프라인 및 8GB RAM급 환경은 현재 논문의 중심 정량 성능 결과가 아니라 시스템 설계 특징과 후속 검증 항목으로 다룬다.

기존 시스템 구현 중심의 설명에서 벗어나, 논문에서는 다음 질문을 중심으로 정리한다.

- 텍스트 기반 RAG는 협동 로봇 실습 매뉴얼 질의에 대해 적절한 텍스트 근거를 검색할 수 있는가?
- 이미지/도식 정보를 추가한 멀티모달 RAG는 텍스트 기반 RAG보다 실습 자료 검색 범위를 확장할 수 있는가?
- 실습 단계 정보를 반영한 context-aware re-ranking은 정답 이미지의 검색 순위를 개선하는가?
- 로컬 LLM 기반 응답 생성은 검색 결과를 실습 안내로 연결하는 보조 기능으로 활용 가능한가?

## 1.1 오프라인 및 제한 자원 서술 원칙

오프라인 구동과 8GB RAM급 제한 환경 목표는 본 시스템의 중요한 설계 특징이다. 그러나 현재 정량 실험은 24GB RAM 개발용 노트북에서 수행되었으므로, 논문에서는 이를 검증 완료된 성능 결과처럼 주장하지 않는다.

따라서 본문에서는 다음과 같이 구분한다.

- 중심 기여: G3 대비 G4의 context-aware multimodal retrieval 성능 개선
- 설계 특징: 외부 API 미사용, 로컬 ChromaDB, Ollama 기반 Q4 양자화 LLM, 전처리/런타임 분리
- 후속 검증: 8GB 이하 장비에서의 실제 메모리 사용량, 응답 속도, 장시간 구동 안정성

즉, 오프라인 및 제한 자원 설계는 논문의 적용 가능성과 실용성을 설명하는 요소로 사용하고, 검색 성능 개선을 대체하는 핵심 정량 결과로 사용하지 않는다.

## 2. 논문 제목 후보

1. A Context-Aware Multimodal Retrieval-Augmented Generation Framework for Collaborative Robot Training
2. Improving Multimodal Retrieval for Collaborative Robot Training Using Context-Aware Retrieval-Augmented Generation

현재 연구 방향과 IEEE Access 투고 가능성을 고려하면 1번 제목이 더 적합하다. `Framework`라는 표현을 통해 단순 앱 구현이 아니라 검색 구조, 멀티모달 정보 결합, 상황 인지형 재순위화 방법을 포함한 연구임을 드러낼 수 있다.

## 3. 데이터셋 구성

실험 데이터는 협동 로봇 실습 매뉴얼을 기반으로 구성하였다.

| 항목 | 내용 |
|---|---|
| 질의 수 | 70개 |
| 질의 유형 | 실습 절차, 메뉴 경로, 설정값, 안전 설정, 설치 및 배선, 상태 확인 등 |
| 정답 라벨 | 정답 텍스트, 정답 이미지, 실습 단계 라벨 |
| 텍스트 데이터 | 매뉴얼에서 추출한 텍스트 chunk |
| 이미지 데이터 | 매뉴얼에서 추출한 이미지/도식 파일 |
| 이미지 경로 기준 | `data/processed/final_refined_data` |
| 평가용 질의셋 | `SCIE용/data/03_question_set_70.csv`, `SCIE용/excel/03_question_set_70.xlsx` |

질의셋은 단순 일반 질의가 아니라, 정답 텍스트와 정답 이미지가 모두 특정될 수 있는 실습 중심 질문으로 구성하였다. 이를 통해 텍스트 검색 성능과 이미지 검색 성능을 분리해서 평가할 수 있도록 하였다.

## 4. 비교군 정의

논문 실험에서는 G1, G2, G3, G4의 네 가지 비교군을 사용한다.

| 비교군 | 이름 | 정의 |
|---|---|---|
| G1 | Keyword Search | 질문과 텍스트 chunk 간 키워드 일치도를 기반으로 검색하는 baseline |
| G2 | Text-only RAG | BGE-M3 텍스트 임베딩을 이용하여 텍스트 chunk만 검색하는 RAG |
| G3 | Multimodal RAG | 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 함께 사용하는 멀티모달 RAG |
| G4 | Context-aware Multimodal RAG | 질문에서 실습 단계를 추정하고, 해당 단계의 page 범위, section heading, keyword context map 기반 re-ranking을 추가한 구조 |

G2와 G3는 텍스트 검색 경로가 동일하므로 텍스트 성능은 동일하게 해석한다. G3의 핵심은 이미지/도식 검색 성능을 추가로 평가할 수 있다는 점이다. G4는 질문에서 실습 단계를 추정한 뒤, 이미지 후보의 순위를 더 적절하게 조정하기 위해 실습 단계 정보를 반영한 구조이다.

## 5. 최종 검색 성능 결과

현재 논문용 기준 결과는 단계 추정 기반 G4 결과를 기준으로 한다. 정답 실습 단계가 주어진 oracle-stage 결과는 실제 앱 사용 조건이 아니므로 최종 논문 비교에서 제외한다. `09_stage_context_map` 및 `10_g4_results`도 초기 예비 실험 성격이므로 최종 논문 결과로 사용하지 않는다.

| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 Keyword Search | 75.7% | 92.9% | 98.6% | 0.827 | - | - | - | - | - | - |
| G2 Text-only RAG | 78.6% | 94.3% | 100.0% | 0.859 | - | - | - | - | - | - |
| G3 Multimodal RAG | 78.6% | 94.3% | 100.0% | 0.859 | 38.6% | 74.3% | 84.3% | 0.534 | 74.3% | 84.3% |
| G4 Context-aware Multimodal RAG | 84.3% | 95.7% | 100.0% | 0.894 | 44.3% | 85.7% | 92.9% | 0.608 | 84.3% | 92.9% |

G3/G4 가중치는 70개 질의의 후보 feature를 이용한 제한된 격자 탐색과 5-fold 내부 검증으로 선택하였다. 따라서 이 표는 내부 파일럿 결과이며, 독립 hold-out 데이터에서의 추가 검증이 필요하다.

## 6. 결과 해석

텍스트 검색은 G1에서도 비교적 높은 성능을 보였고, G2에서 Text Recall@1과 Text MRR이 개선되었다. 이는 협동 로봇 매뉴얼 질의가 메뉴명, 기능명, 설정값 등 명시적인 용어를 많이 포함하기 때문으로 해석할 수 있다.

G2와 G3의 텍스트 검색 성능이 동일한 이유는 두 비교군이 동일한 BGE-M3 텍스트 임베딩, 동일한 ChromaDB 텍스트 collection, 동일한 텍스트 chunk, 동일한 Top-k 검색 방식을 사용했기 때문이다. G3는 텍스트 검색기를 새로 바꾼 방식이 아니라, G2의 텍스트 검색 경로를 유지한 상태에서 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 추가한 멀티모달 확장 구조이다. 따라서 G2/G3의 Text Recall@k와 Text MRR이 동일한 것은 실험 설계상 자연스러운 결과이며, G3의 기여는 텍스트 검색 향상이 아니라 이미지/도식 후보 검색 추가에 있다.

G3에서는 이미지 검색이 추가되었고, BBox를 후보 필터로 제한한 뒤 SigLIP으로 매핑 순위를 정한 결과 Image Recall@1은 38.6%, Image MRR은 0.534로 나타났다. 정답 이미지를 1위에 배치한 비율은 여전히 절반 미만이다.

G4에서는 질문에서 실습 단계를 추정한 뒤, 해당 단계의 page 범위, section heading, keyword 정보를 기반으로 re-ranking을 수행하였다. 그 결과 G3 대비 Image Recall@5는 74.3%에서 85.7%로, Image Recall@10은 84.3%에서 92.9%로, Image MRR은 0.534에서 0.608로 개선되었다. 다만 Image Recall@1은 44.3%로 절반 미만이므로, G4는 이미지 검색 문제를 해결한 방식이 아니라 관련 이미지 후보를 Top-5 또는 Top-10 안으로 더 잘 끌어올린 방식으로 해석한다.

따라서 현재 결과는 다음과 같이 요약할 수 있다.

- 텍스트 검색은 이미 비교적 안정적이다.
- 멀티모달 RAG의 병목은 이미지 검색 순위와 텍스트-이미지 정렬 품질이다.
- G4의 상황 정보 기반 re-ranking은 정답 이미지를 Top-5 또는 Top-10 후보로 올리는 데 일부 효과가 있었다.
- 다만 같은 page 또는 같은 section 안에 유사 이미지가 많은 경우에는 여전히 image-level distinction이 부족하다.

## 7. G4 설계 핵심

G4는 정답 이미지 파일명이나 정답 chunk ID를 직접 사용하지 않는다. 먼저 질문과 실습 단계 context profile 간 BGE-M3 의미 유사도를 비교하여 실습 단계를 추정하고, 이후 실습 단계별로 다음 정보를 매핑한 context map을 사용한다.

- 관련 텍스트 page 범위
- 관련 이미지 page 범위
- section heading
- 핵심 keyword
- 매핑 근거

이 매핑표는 `SCIE용/data/11_stage_context_map_manual.csv`와 `SCIE용/excel/11_stage_context_map_manual.xlsx`에 정리되어 있다. 논문에서는 이를 실습 단계 context map으로 설명할 수 있다.

G4 re-ranking은 다음 방향으로 작동한다.

- 질문에서 추정된 실습 단계와 관련된 page 범위에 있는 텍스트/이미지 후보에 가중치를 부여한다.
- section heading과 keyword가 일치하는 후보의 점수를 보정한다.
- 기존 G3의 텍스트 검색, 이미지 검색, page proximity, 텍스트-이미지 매핑 점수는 유지한다.
- 단계 추정 신뢰도가 낮거나 후보가 애매하면 G4를 강제 적용하지 않고 G3 방식으로 fallback한다.
- 상황 정보는 단계 page 범위의 이미지를 후보로 보완하고, 기존 G3 후보와 함께 순위를 재조정한다.

## 8. G4 개선 사례

G4의 후보 순위 개선 효과를 설명하기 위해 다음 세 가지 사례를 논문에 사용할 수 있다. 개선 사례는 G4가 질문에서 추정한 실습 단계, page 범위, section heading, keyword context를 이용해 관련 이미지 후보를 실제로 더 높은 순위로 조정한다는 점을 보여준다. 즉, 정량 지표의 개선 폭만 제시하는 것이 아니라 G4가 왜 작동했는지를 설명하기 위한 근거이다.

| 사례 | 질문 번호 | 실습 단계 | 정답 이미지 | G3 순위 | G4 순위 | 해석 |
|---|---|---|---|---:|---:|---|
| 티치 펜던트/USB 데이터 관리 | Q31 | 티치 펜던트/USB 데이터 관리 | `page_103_img_0_0.jpeg` | Top-10 밖 | 3위 | 질문 기반 단계 추정이 맞았고 USB 관련 context가 반영되어 Top-5 안으로 상승 |
| UI/시스템 정보 확인 | Q23 | UI/시스템 정보 확인 | `page_167_img_3_0.jpeg` | Top-10 밖 | 5위 | 시스템 정보와 시간 기능 관련 context가 반영되어 Top-5 안으로 상승 |
| 안전/전원/접지 | Q02 | 안전/전원/접지 | `page_403_img_0_0.jpeg` | Top-10 밖 | 5위 | 접지, 전원, 컨트롤러 관련 context가 반영되어 Top-5 안으로 상승 |

이 사례들은 G4가 일부 질의에서 실제 실습 단계 맥락을 이용해 정답 이미지의 순위를 끌어올렸다는 근거로 사용할 수 있다. 다만 전체 Image Recall@1은 여전히 낮으므로, G4의 성과는 정답 이미지를 항상 1순위로 찾는 것이 아니라 관련 후보를 더 높은 순위권에 포함시키는 것으로 제한해 해석한다.

## 9. G4 실패 사례와 한계

G4에서도 실패한 사례는 논문에서 한계 및 향후 연구로 정리할 수 있다. 실패 사례를 함께 제시하는 이유는 G4가 이미지 검색 문제를 완전히 해결한 것이 아니라, page-level 및 section-level context를 이용해 후보 순위를 보정하는 방식임을 명확히 하기 위해서이다. 특히 같은 page의 유사 이미지, 세부 화면 단서 부족, 단계 추정 오류는 현재 G4의 주요 한계로 정리할 수 있다.

| 사례 | 질문 번호 | 실습 단계 | 정답 이미지 | 문제 |
|---|---|---|---|---|
| 티치 펜던트 상태 확인 | Q10 | 티치 펜던트/상태 확인 | `page_332_img_0_0.jpeg` | Status 관련 범위는 맞지만 실제 정답 화면 이미지가 Top-10에 포함되지 않음 |
| 케이블 방수 | Q28 | 설치/케이블 방수 | `page_405_img_0_0.jpeg` | 같은 page의 다른 이미지들은 검색되었지만 정확한 세부 이미지는 선택하지 못함 |
| 시스템 관리/로그 | Q15 | 시스템 관리/로그 | `page_340_img_0_0.jpeg` | 질문 기반 단계 추정이 UI/시스템 정보 확인으로 치우쳐 정답 이미지가 Top-10에 포함되지 않음 |

현재 G4는 page-level 또는 section-level context를 반영하는 데는 효과가 있으나, 같은 page 안의 여러 이미지 중 정확한 이미지를 구분하는 능력은 아직 부족하다. BBox는 공간 후보 필터이므로 필터 안의 유사 이미지를 직접 구분하지 않는다. 이를 개선하려면 이미지 caption, BBox 주변 텍스트, 이미지 순서, 세부 단계 라벨을 추가로 활용해야 한다.

## 10. 평가 기준

검색 성능은 다음 지표로 평가한다.

| 지표 | 의미 |
|---|---|
| Text Recall@k | relaxed 기준에서 Top-k 텍스트 후보 안에 정답 또는 동등한 관련 정보가 포함되는 비율 |
| Image Recall@k | strict 기준에서 Top-k 이미지 후보 안에 정답 이미지 파일명이 포함되는 비율 |
| Text MRR | relaxed 기준에서 정답 또는 관련 텍스트가 높은 순위에 위치하는 정도 |
| Image MRR | strict 기준에서 정답 이미지 파일명이 높은 순위에 위치하는 정도 |
| Both@k | relaxed text hit와 strict image hit가 동시에 만족되는 비율 |

텍스트 검색 평가는 relaxed 기준을 사용하였다. 즉, 정답 문장과 완전 일치하지 않더라도 같은 page 또는 section에 해당하거나, 핵심 keyword를 포함하거나, 의미적으로 동일한 절차 및 설정 정보를 담고 있으면 정답으로 인정하였다. 반면 이미지 검색 평가는 정답 이미지 파일명 기반 strict 기준을 사용하였다. 같은 page의 유사 이미지가 검색되더라도 정답 파일명과 다르면 오답으로 처리하였다. 따라서 논문에서는 텍스트 지표를 `Text Recall@k (relaxed)`, 이미지 지표를 `Image Recall@k (strict)`로 명확히 설명한다.

응답 품질 평가는 검색 성능과 별도로 진행한다. 평가 항목은 다음 5개이다.

- 정확성
- 구체성
- 실습 단계 적합성
- 안전성
- 이해 용이성

각 항목은 1~5점으로 평가하고, 평균 점수를 기준으로 응답 품질을 비교한다. 현재 Qwen, Gemma, Llama를 대상으로 G2/G3/G4 조건의 630개 응답에 대한 rubric 기반 1차 평가를 완료하였다.

| 비교군 | 모델 | 평가 수 | 평균 점수 | O | △ | X |
|---|---|---:|---:|---:|---:|---:|
| G2 Text-only RAG | Qwen | 70 | 4.05 | 49 | 13 | 8 |
| G2 Text-only RAG | Gemma | 70 | 3.59 | 27 | 31 | 12 |
| G2 Text-only RAG | Llama | 70 | 3.62 | 24 | 33 | 13 |
| G3 Multimodal RAG | Qwen | 70 | 4.01 | 47 | 15 | 8 |
| G3 Multimodal RAG | Gemma | 70 | 3.56 | 27 | 29 | 14 |
| G3 Multimodal RAG | Llama | 70 | 3.60 | 28 | 27 | 15 |
| G4 Context-aware Multimodal RAG | Qwen | 70 | 3.99 | 47 | 14 | 9 |
| G4 Context-aware Multimodal RAG | Gemma | 70 | 3.59 | 27 | 31 | 12 |
| G4 Context-aware Multimodal RAG | Llama | 70 | 3.62 | 31 | 26 | 13 |

이 평가는 정의된 rubric에 따라 630개 응답을 비교한 보조 분석이다. 최신 재생성 결과에서는 G4가 검색 성능은 개선했지만, 생성 응답 품질은 Qwen 기준 G3 4.01점에서 G4 3.99점으로 거의 유지되는 수준이었다. 따라서 응답 품질 결과는 본 논문의 중심 성과가 아니라, 검색 성능 개선이 생성 품질 향상으로 항상 직접 연결되지는 않는다는 보조 분석으로 제시한다.

## 11. 논문 기여점 정리

현재 결과를 바탕으로 논문 기여점은 다음과 같이 정리할 수 있다.

1. 협동 로봇 실습 매뉴얼을 대상으로 텍스트, 이미지/도식, 실습 단계 라벨을 포함한 평가용 질의셋을 구축하였다.
2. Text-only RAG, Multimodal RAG, Context-aware Multimodal RAG를 동일 질의셋에서 비교할 수 있는 실험 구조를 설계하였다.
3. 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 결합한 멀티모달 검색 구조를 구현하였다.
4. 질문 기반 실습 단계 추정과 단계별 context map 기반 re-ranking을 통해 G3 대비 G4의 이미지 후보 포함률과 평균 순위를 개선하였다.
5. 생성 응답 품질 평가는 보조 분석으로 분리하고, 개선 사례와 실패 사례를 통해 상황 인지형 멀티모달 검색의 효과와 한계를 함께 분석하였다.

## 12. 논문 초안 작성 시 주의점

논문에서는 다음 표현을 피해야 한다.

- 단순히 "챗봇을 만들었다"는 설명
- G4가 생성 응답 품질을 일관되게 향상시켰다는 주장
- 이미지 검색 성능이 완전히 해결되었다는 과도한 주장
- G4가 모든 질의에서 개선되었다는 주장
- 09/10번 예비 실험 결과를 최종 G4 결과처럼 사용하는 것
- 8GB RAM급 환경에서 성능 검증이 완료되었다는 주장

대신 다음 방향으로 서술하는 것이 적절하다.

- 제안 시스템은 협동 로봇 실습 환경을 위한 context-aware multimodal RAG framework이다.
- 텍스트 검색은 안정적이지만 이미지 검색 순위가 전체 멀티모달 성능의 병목이다.
- G4는 질문 기반 실습 단계 추정과 context map을 이용해 이미지 후보의 Top-5/Top-10 포함률과 평균 순위를 개선하였다.
- 다만 Image Recall@1은 44.3%로 절반 미만이어서, 이미지 검색 문제를 완전히 해결했다고 주장하지 않는다.
- 응답 품질 평가는 검색 성능 결과를 보완하는 보조 분석으로만 제시한다.
- 동일 page 또는 section 내 유사 이미지 구분은 향후 개선이 필요한 한계이다.
- 오프라인 및 8GB RAM급 제한 환경은 설계 목표로 제시하고, 실제 8GB 이하 장비에서의 속도와 메모리 측정은 후속 검증으로 둔다.

## 13. 논문 초안 구조 제안

### Abstract

연구 배경, 문제점, 제안 방법, G1/G3/G4 비교 결과, 주요 개선 수치를 간결하게 제시한다.

### 1. Introduction

협동 로봇 실습 교육에서 매뉴얼 기반 안내의 필요성, 텍스트 기반 RAG의 한계, 이미지/도식 및 실습 단계 정보의 필요성을 설명한다.

### 2. Related Work

RAG, multimodal retrieval, educational guidance systems, collaborative robot training 관련 연구를 정리한다.

### 3. Proposed Framework

전체 시스템 구조, 텍스트 전처리, 이미지 전처리, ChromaDB 인덱싱, G3 멀티모달 검색 구조, G4 context-aware re-ranking 구조를 설명한다.

### 4. Experimental Setup

70개 질의셋, 정답 텍스트/이미지 라벨, G1/G2/G3/G4 비교군, 평가 지표를 설명한다.

### 5. Results and Discussion

G1/G2/G3/G4 정량 결과, G4 개선 사례, 실패 사례, 한계 분석을 제시한다.

### 6. Auxiliary Response Quality Evaluation

Qwen, Gemma, Llama 모델을 대상으로 응답 정확성, 구체성, 실습 단계 적합성, 안전성, 이해 용이성을 평가한다. 이 절은 중심 실험 결과가 아니라 로컬 LLM 기반 실습 안내의 가능성과 한계를 확인하는 보조 분석으로 배치한다. 평가 방식과 한계를 명시하고, 전문가 평가 또는 교육 효과 검증 결과로 해석하지 않는다.

### 7. Conclusion

연구 결과를 요약하고, 이미지 수준 구분 능력 개선, caption/bbox 활용, 사용자 평가 확장 등을 향후 연구로 제시한다.

## 14. 현재 초안 작성 가능 여부

현재 상태에서 Method, Experimental Setup, Retrieval Results, Response Quality Evaluation 초안은 모두 작성 가능하다. Response Quality Evaluation은 rubric 기반 보조 분석으로만 제시하고, 연구의 중심 결과는 검색 성능 비교에 둔다.

따라서 현재 논문 초안 작성 우선순위는 다음과 같다.

1. Abstract 초안 작성
2. Method 초안 작성
3. Experimental Setup 초안 작성
4. Retrieval Results and Discussion 초안 작성
5. rubric 기반 응답 품질 평가의 범위와 한계를 명시

## 15. 논문 기준으로 사용할 파일

| 용도 | 파일 |
|---|---|
| 전체 계획 | `SCIE용/00_plan.md` |
| 질의셋 | `SCIE용/data/03_question_set_70.csv`, `SCIE용/excel/03_question_set_70.xlsx` |
| 비교군 정의 | `SCIE용/05_experiment_groups.md` |
| 평가 지표 | `SCIE용/06_metrics.md` |
| G3 파일럿 결과 | `SCIE용/07_pilot_results.md` |
| G4 설계 방향 | `SCIE용/08_context_rerank_results.md` |
| 최종 G4 context map | `SCIE용/data/11_stage_context_map_manual.csv`, `SCIE용/excel/11_stage_context_map_manual.xlsx` |
| 최종 G4 결과 | `SCIE용/30_g4_auto_results.md` |
| G4 단계 추정 결과 | `SCIE용/29_stage_classifier_results.md`, `SCIE용/excel/29_stage_classifier_eval.xlsx` |
| G1/G2/G3/G4 최종 비교 | `SCIE용/15_g1_g2_g3_g4_results.md` |
| G4 사례 분석 | `SCIE용/16_g4_case_analysis.md` |
| 응답 품질 평가 기준 | `SCIE용/17_response_quality_eval_criteria.md` |
| 응답 품질 평가 템플릿 | `SCIE용/excel/17_response_quality_eval_template.xlsx` |
| 응답 품질 평가 결과 | `SCIE용/22_response_quality_eval_results.md`, `SCIE용/excel/22_response_quality_eval_results.xlsx` |
논문 최종 결과로는 `11`, `15`, `16`, `17`, `22`, `29`, `30`번 산출물을 중심으로 사용한다.
