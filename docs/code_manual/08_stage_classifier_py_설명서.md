# `src/stage_classifier.py` 상세 설명서

## 1. 파일 역할

`stage_classifier.py`는 사용자 질문을 미리 정의된 실습 단계 profile과 비교해 가장 관련 있는 단계를 추정한다.

별도의 학습된 분류 모델을 두는 방식이 아니라 다음 흐름을 사용한다.

1. 단계별 페이지·섹션·본문·동작 키워드를 하나의 profile 문장으로 구성
2. BGE-M3로 단계 profile 임베딩 사전 계산
3. 질문을 BGE-M3로 임베딩
4. 질문과 모든 단계 profile의 cosine 유사도 계산
5. 최고 점수와 1·2위 점수 차이가 기준을 통과할 때만 G4 단계로 채택

기준을 통과하지 못하면 단계 label을 `None`으로 반환하여 검색 코드가 G3로 폴백하게 한다.

## 2. 분류 기준 상수

| 상수 | 값 | 의미 |
|---|---:|---|
| `DEFAULT_STAGE_TOP_K` | 3 | 화면과 결과에 보관할 상위 단계 후보 수 |
| `DEFAULT_STAGE_MIN_SCORE` | 0.45 | 최고 단계의 최소 cosine 점수 |
| `DEFAULT_STAGE_MIN_MARGIN` | 0.03 | 1위와 2위 단계 점수의 최소 차이 |

두 기준을 모두 만족해야 `used=True`가 된다.

## 3. 함수 설명

### 3.1 `_text(value)`

`None`을 빈 문자열로 처리하고 나머지 값을 문자열로 바꾼 뒤 앞뒤 공백을 제거한다.

단계 map의 숫자·문자열·빈 값을 같은 방식으로 다루기 위한 내부 보조 함수이다.

### 3.2 `_join_terms(values)`

#### 목적

단계 profile을 구성하는 여러 문자열과 리스트를 하나의 공백 구분 문자열로 합친다.

#### 처리

1. 값이 list, tuple, set이면 내부 항목 각각을 `_text()`로 정리한다.
2. 단일 값이면 빈 문자열이 아닐 때 추가한다.
3. 모든 term을 공백으로 연결한다.

중복 term 제거는 이 함수에서 수행하지 않는다.

### 3.3 `build_stage_profiles(map_path)`

#### 목적

CSV 단계 문맥표를 단계 분류에 사용할 profile 리스트로 바꾼다.

#### 처리

1. `rag_search.load_stage_context_map()`으로 CSV를 읽는다.
2. 단계명을 기준으로 정렬한다.
3. 각 단계에서 다음 정보를 합친다.
   - stage ID
   - 단계명
   - 섹션 term
   - 본문 term
   - 동작·질문 term
   - 근거 설명
4. 단계명, stage ID, profile 텍스트, 원본 context를 하나의 딕셔너리로 저장한다.

#### 반환 구조

```json
{
  "stage": "로봇 설치",
  "stage_id": "S01",
  "profile_text": "S01 로봇 설치 ...",
  "context": {"text_ranges": [], "image_ranges": [], "...": "..."}
}
```

질문 번호, 정답 이미지 파일명, 정답 chunk ID는 profile에 포함하지 않는다.

### 3.4 `encode_stage_profiles(embedder, profiles)`

#### 목적

앱 시작 시 단계 profile 전체를 한 번 임베딩해 질문마다 반복 계산하지 않도록 한다.

#### 반환

- profile이 없으면 빈 리스트
- 있으면 `embedder.encode(texts)` 결과

`app_runtime.py`의 Streamlit resource cache 안에서 호출되므로 일반적인 앱 사용 중 한 번만 계산된다.

### 3.5 `cosine_similarity(vec_a, vec_b)`

#### 목적

두 벡터의 cosine 유사도를 Python 연산으로 계산한다.

#### 계산

```text
dot(a, b) / (norm(a) × norm(b))
```

둘 중 하나의 norm이 0이면 0을 반환한다. NumPy나 sklearn을 호출하지 않고 iterable 숫자 벡터에 직접 동작한다.

### 3.6 `classify_stage(...)`

#### 매개변수

- `question`: 사용자 질문
- `embedder`: BGE-M3 SentenceTransformer
- `profiles`: `build_stage_profiles()` 결과
- `profile_embeddings`: 단계 profile 임베딩
- `top_k`: 보관할 상위 후보 수
- `min_score`: 최고 점수 기준
- `min_margin`: 1·2위 점수 차이 기준

#### 입력 검증과 폴백

다음 중 하나이면 분류를 수행하지 않는다.

- 질문이 비어 있음
- profile이 없음
- profile 수와 embedding 수가 다름

이 경우 `stage_label=None`, `used=False`, 이유 `stage profile not available`을 반환한다.

#### 정상 분류 순서

1. 질문을 BGE-M3로 임베딩한다.
2. 모든 단계 profile embedding과 cosine 유사도를 계산한다.
3. 단계명, ID, 소수점 넷째 자리 점수를 후보에 저장한다.
4. 점수 내림차순으로 정렬한다.
5. 상위 `top_k`를 선택한다.
6. 최고 점수와 두 번째 점수의 차이 `margin`을 계산한다.
7. 최고 점수 ≥ 0.45이고 margin ≥ 0.03인지 확인한다.

#### 반환

| key | 의미 |
|---|---|
| `stage_label` | 기준 통과 시 최종 단계, 실패 시 `None` |
| `predicted_stage` | 기준과 무관한 최고 점수 단계 |
| `score` | 최고 단계 점수 |
| `margin` | 1위와 2위 점수 차이 |
| `used` | G4 적용 가능 여부 |
| `top_candidates` | 상위 단계 후보 |
| `reason` | 기준 통과 또는 실패 이유 |

`predicted_stage`와 `stage_label`을 구분하는 것이 중요하다. 가장 비슷한 단계가 있어도 신뢰 기준을 통과하지 못하면 G4에는 사용하지 않는다.

## 4. 앱과의 연결

```text
app_runtime.load_stage_classifier_resources()
  |- build_stage_profiles()
  `- encode_stage_profiles()

app_runtime.resolve_stage_label()
  `- classify_stage()
       |- 기준 통과: stage_label 전달 -> G4
       `- 기준 실패: None 전달 -> G3 fallback
```

## 5. 이 방식이 정답 누수가 아닌 이유

분류기는 질문별 정답을 저장하지 않는다. 단계 profile에는 다음과 같은 일반적인 매뉴얼 구조 정보만 들어간다.

- 단계명
- 관련 페이지 범위
- 섹션·본문·동작 키워드
- 단계 정의 근거

따라서 새로운 질문도 같은 BGE-M3 유사도 기준으로 분류된다. 다만 profile과 임계값이 내부 데이터에 맞춰 설계되었으므로 외부 매뉴얼 일반화는 별도 검증이 필요하다.

## 6. 주의사항

1. BGE-M3 임베딩 품질과 단계 profile 문구가 분류 결과를 결정한다.
2. profile에 비슷한 단어가 많은 단계가 여러 개 있으면 margin이 작아져 G3로 폴백할 수 있다.
3. `top_k=1`이면 두 번째 점수가 0으로 처리되어 margin이 실제보다 크게 보일 수 있으므로 기본값 3을 유지하는 편이 안전하다.
4. 단계 context CSV가 바뀌면 Streamlit cache를 비우거나 앱을 재시작해야 한다.
5. 분류 점수는 확률이 아니라 embedding cosine 유사도이다.

