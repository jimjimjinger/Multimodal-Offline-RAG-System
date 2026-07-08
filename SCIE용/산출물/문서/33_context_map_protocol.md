# G4 Context Map 구축 절차

## 목적

이 문서는 G4 상황 인지형 멀티모달 RAG에서 사용하는 stage context map의 구축 절차를 논문 Method에 사용할 수 있도록 정리한 문서이다. 핵심은 context map이 정답 이미지 파일명이나 정답 chunk ID를 직접 사용하지 않고, 매뉴얼의 구조와 실습 단계 의미를 기준으로 사전에 구성되었다는 점을 명확히 하는 것이다.

## Context Map의 역할

G4는 G3에서 생성한 텍스트 및 이미지 후보를 그대로 사용하되, 질문에서 자동 추정한 실습 단계와 관련된 문맥 정보를 이용해 후보 순위를 재조정한다.

Context map은 다음 정보를 제공한다.

| 항목 | 역할 |
|---|---|
| 실습 단계명 | 질문이 어떤 실습 단계와 관련되는지 표현 |
| 텍스트 page 범위 | 해당 단계의 설명 텍스트가 주로 위치한 매뉴얼 범위 |
| 이미지 page 범위 | 해당 단계의 이미지/도식이 주로 위치한 매뉴얼 범위 |
| section keyword | 매뉴얼 section heading 또는 메뉴명 |
| 본문 keyword | 해당 단계 설명에서 반복되는 핵심 용어 |
| 동작/질문 keyword | 사용자가 물을 가능성이 높은 동작, 절차, 설정 표현 |
| 가중치 | 단계별 context 신뢰도 또는 중요도 |
| 근거 | 매뉴얼 section 또는 page 범위를 선택한 이유 |

## 사용한 정보

Context map 구축에는 다음 정보만 사용한다.

| 정보 | 사용 여부 | 설명 |
|---|---:|---|
| 매뉴얼 section heading | O | 실습 단계와 매뉴얼 구조를 연결하기 위해 사용 |
| 매뉴얼 page range | O | 관련 텍스트/이미지 후보의 page-level relevance 계산에 사용 |
| 매뉴얼 본문 keyword | O | 후보 텍스트와 이미지 주변 문맥의 keyword match 계산에 사용 |
| 실습 단계명 | O | 자동 단계 분류와 context map key로 사용 |
| 정답 이미지 파일명 | X | context map 구축과 re-ranking에 사용하지 않음 |
| 정답 chunk ID | X | context map 구축과 re-ranking에 사용하지 않음 |
| 질문 번호 | X | 특정 질의에만 맞춘 rule을 만들지 않음 |
| 평가 후 결과 | X | 평가 결과를 보고 context map을 수정하지 않음 |

## 구축 절차

1. 협동 로봇 실습 매뉴얼의 목차, section heading, page 범위를 확인한다.
2. 실습 흐름을 기준으로 설치, 전원, 티치 펜던트, 직접 교시, 안전 설정, I/O, 시스템 관리 등 주요 실습 단계를 정의한다.
3. 각 실습 단계에 대해 관련 텍스트 page 범위와 이미지 page 범위를 매뉴얼 기준으로 지정한다.
4. 해당 page 및 section에서 반복되는 메뉴명, 기능명, 설정값, 안전 용어를 keyword로 정리한다.
5. 질문 번호, 정답 이미지 파일명, 정답 chunk ID는 매핑표에 포함하지 않는다.
6. 구축된 context map을 고정한 뒤 G4 검색 평가를 수행한다.
7. 평가 후에는 본 실험 결과를 개선하기 위해 context map을 수정하지 않는다.

## G4 자동 단계 분류와의 연결

G4에서는 사용자가 직접 실습 단계를 선택하지 않는다. 질문이 입력되면 BGE-M3를 이용하여 질문과 각 실습 단계 context profile의 의미 유사도를 계산한다.

```text
질문
  -> BGE-M3 embedding
  -> stage context profile embedding과 cosine similarity 계산
  -> Top stage 후보 산출
  -> score와 margin 기준 통과 시 G4 적용
  -> 기준 미달 시 G3 fallback
```

Stage context profile은 stage context map의 다음 항목으로 구성한다.

- 실습 단계명
- section keyword
- 본문 keyword
- 동작/질문 keyword
- 근거 문장

이 과정에서도 정답 이미지 파일명이나 질문 번호는 사용하지 않는다.

## Re-ranking 방식

G4는 context map을 이용해 텍스트와 이미지 후보를 다음 기준으로 보정한다.

| 점수 | 설명 |
|---|---|
| page range score | 후보의 page가 해당 실습 단계 page 범위와 가까운지 평가 |
| keyword score | 후보 텍스트 또는 이미지 주변 문맥이 단계 keyword를 포함하는지 평가 |
| section score | 후보가 관련 section heading과 연결되는지 평가 |
| stage query score | 실습 단계명과 질문을 결합한 질의로 이미지 후보를 추가 검색한 점수 |

최종 점수는 기존 G3 score에 stage context score를 더하는 방식으로 계산한다. 따라서 G4는 정답을 직접 선택하는 방식이 아니라, G3 후보의 순위를 실습 단계 문맥에 따라 조정하는 방식이다.

## 실험 누수 방지 원칙

논문에는 다음 원칙을 명시한다.

1. Context map에는 정답 이미지 파일명과 정답 chunk ID를 포함하지 않는다.
2. Context map은 평가 결과를 본 뒤 질의별로 수정하지 않는다.
3. 자동 단계 분류가 낮은 신뢰도라고 판단되면 G4를 강제 적용하지 않고 G3로 fallback한다.
4. 정답 실습 단계가 주어졌다고 가정한 oracle-stage 결과는 메인 비교군에서 제외하고 참고 상한 성능으로만 해석한다.

## 논문 Method 문장 초안

> To avoid label leakage, the stage context map was constructed using only manual-level information, including stage names, page ranges, section headings, and keywords. Correct image filenames, correct chunk identifiers, and question IDs were not included in the context map. The map was fixed before running the G4 evaluation and was not modified based on the retrieval results.

## 관련 파일

| 파일 | 설명 |
|---|---|
| `SCIE용/data/11_stage_context_map_manual.csv` | G4 stage context map 원본 CSV |
| `SCIE용/excel/11_stage_context_map_manual.xlsx` | 사람이 확인하기 쉬운 context map |
| `SCIE용/11_stage_context_map_manual.md` | context map 요약 문서 |
| `src/stage_classifier.py` | 자동 실습 단계 분류 코드 |
| `src/rag_search.py` | G4 re-ranking 코드 |
| `scripts/evaluate_stage_classifier.py` | 단계 자동 분류 평가 |
| `scripts/evaluate_scie_g4_auto_retrieval.py` | 자동 단계 분류 기반 G4 검색 평가 |
