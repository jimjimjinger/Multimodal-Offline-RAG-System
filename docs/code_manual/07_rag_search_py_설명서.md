# `src/rag_search.py` 상세 설명서

## 1. 파일 역할

`rag_search.py`는 앱에서 사용자 질문을 받은 뒤 실제 검색을 수행하는 핵심 모듈이다.

이 파일은 다음 작업을 담당한다.

1. ChromaDB 컬렉션을 정확 전수 검색 wrapper로 변환
2. 질문과 관련된 텍스트 근거 검색
3. 세 경로에서 이미지 후보 수집
4. G3 이미지 기본 점수 계산
5. 단계 문맥이 있으면 G4 텍스트·이미지 재순위화
6. 로컬 LLM에 전달할 문맥과 화면에 표시할 이미지 반환

## 2. 검색 상수

### 2.1 검색 개수

| 상수 | 값 | 의미 |
|---|---:|---|
| `ANSWER_TOP_K` | 5 | LLM 답변과 화면 원문에 사용할 텍스트 수 |
| `IMAGE_TEXT_TOP_K` | 60 | 이미지 후보 수집용 텍스트 검색 수 |
| `IMAGE_COLLECTION_TOP_K` | 80 | 이미지 전용 컬렉션 검색 수 |
| `IMAGE_RESULTS_LIMIT` | 10 | 최종 표시 이미지 수 |
| `STAGE_TEXT_TOP_K` | 30 | G4 텍스트 재순위화 전 후보 수 |
| `TEXT_RANK_SCORE_WINDOW` | 30 | 텍스트 순위를 이미지 점수로 바꾸는 범위 |
| `STAGE_BASE_RANK_WINDOW` | 120 | 단계 문맥 가산점을 정상 적용할 기본 후보 순위 범위 |

### 2.2 G3 이미지 기본 점수

```text
base_score =
    0.25 × image_search_score
  + 0.15 × text_rank_score
  + 0.50 × page_score
  + 0.05 × mapping_score
  + 0.05 × diagram_score
```

| 신호 | 의미 |
|---|---|
| `image_search_score` | 이미지 전용 컬렉션에서 질문과 가까운 정도 |
| `text_rank_score` | 상위 텍스트 청크에 사전 연결된 이미지인지 |
| `page_score` | 상위 텍스트와 같은 페이지 또는 인접 페이지인지 |
| `mapping_score` | 전처리에서 저장한 SigLIP 텍스트-이미지 유사도 |
| `diagram_score` | 이미지 자체가 기술 도면으로 판별된 정도 |

### 2.3 G4 이미지 점수

```text
final_score =
    base_score
  + 0.50 × stage_score × rank_factor
  + 0.25 × stage_page_score
```

단계 문맥을 사용하지 않으면 `final_score=base_score`가 된다.

## 3. `ExactVectorCollection` 클래스

### 3.1 클래스 목적

ChromaDB의 approximate HNSW query를 직접 사용하지 않고, 저장된 모든 임베딩과 질문 임베딩의 거리를 계산하여 재현 가능한 정확 순위를 만든다.

작은 연구 데이터에서는 순위 안정성을 얻을 수 있지만, 컬렉션 전체 임베딩을 RAM에 올리고 매 질문마다 전수 비교하므로 데이터가 커질수록 비용이 증가한다.

### 3.2 `__init__(self, collection)`

#### 처리 순서

1. Chroma collection에서 임베딩, 문서, 메타데이터, ID 전체를 가져온다.
2. 임베딩이 없으면 `RuntimeError`를 발생시킨다.
3. ID·문서·메타데이터·임베딩 길이가 다르면 오류를 발생시킨다.
4. 동일 거리 tie를 안정적으로 처리하기 위해 ID 오름차순으로 저장 순서를 맞춘다.
5. 임베딩을 `float64` NumPy 배열로 보관한다.
6. 컬렉션의 HNSW 공간 설정을 읽는다. 설정이 없으면 `l2`를 사용한다.
7. cosine 계산에 사용할 각 저장 임베딩 norm을 미리 계산한다.

#### 메모리 영향

텍스트와 이미지 컬렉션 wrapper를 만들 때 임베딩 전체가 각각 메모리에 올라간다.

### 3.3 `count(self)`

저장된 ID 수, 즉 wrapper가 검색할 전체 record 수를 반환한다.

### 3.4 `get(self, *args, **kwargs)`

원본 Chroma collection의 `get()`을 그대로 호출한다. wrapper 밖에서 원본 record를 조회할 수 있게 유지한 통과 메서드이다.

### 3.5 `_distances(self, query_embedding)`

컬렉션 공간 설정에 따라 질문과 전체 저장 임베딩의 거리를 계산한다.

- `cosine`: `1 - cosine similarity`
- `ip`: `1 - inner product`
- 기본 `l2`: 각 차이의 제곱합

기본 L2는 제곱근을 계산하지 않은 squared Euclidean distance이다. 순위는 일반 Euclidean distance와 동일하다.

### 3.6 `query(self, query_embeddings, n_results=10, include=None, **kwargs)`

#### 입력 검증

1. 별도 keyword query 옵션이 들어오면 지원하지 않는다고 `ValueError`를 발생시킨다.
2. 1차원 질문 임베딩은 2차원 batch 형태로 바꾼다.
3. 질문 차원과 DB 임베딩 차원이 다르면 오류를 발생시킨다.

#### 결과 구성

`include`가 없으면 ID, 메타데이터, 문서, 거리를 반환한다. 필요하면 임베딩도 포함할 수 있다.

각 질문마다 다음을 수행한다.

1. 전체 거리 계산
2. 거리 오름차순, ID 오름차순으로 정렬
3. 요청 수만큼 선택
4. Chroma query와 유사한 중첩 리스트 구조로 반환

요청 수가 collection 크기보다 크면 실제 record 수로 제한한다.

## 4. 컬렉션과 기본 변환 함수

### 4.1 `get_collection_or_none(client, name)`

Chroma client에서 이름으로 collection을 가져온다. 실패하면 예외를 전파하지 않고 `None`을 반환한다.

이미지 전용 collection이 아직 구축되지 않았을 때 텍스트 검색만 계속할 수 있도록 사용한다.

### 4.2 `open_rag_collections(client)`

1. 텍스트 collection은 반드시 가져와 `ExactVectorCollection`으로 감싼다.
2. 이미지 collection은 있으면 wrapper로 감싸고, 없으면 `None`으로 둔다.
3. `(text_collection, image_collection)`을 반환한다.

텍스트 collection이 없으면 앱 로딩 자체가 실패한다.

### 4.3 `parse_json(value, default)`

DB 메타데이터에 문자열로 저장된 JSON을 Python 객체로 바꾼다.

- 값이 `None` 또는 빈 문자열이면 `default`
- JSON 파싱 성공 시 파싱 결과
- 타입 오류 또는 JSON 형식 오류 시 `default`

### 4.4 `to_float(value, default=0.0)`

값을 `float`로 바꾼다. 타입 또는 값 오류가 나면 기본값을 반환한다.

### 4.5 `distance_to_score(distance)`

벡터 거리를 큰 값일수록 낮은 0~1 유사 점수로 바꾼다.

```text
score = 1 / (1 + max(0, distance))
```

거리 값이 없으면 0을 반환한다.

### 4.6 `query_first(result, key)`

Chroma query 결과는 질문 batch를 고려해 `[[...]]` 구조를 사용한다. 이 함수는 지정한 key의 첫 번째 질문 결과 리스트를 꺼낸다.

값이 없으면 빈 리스트를 반환한다.

### 4.7 `make_context(retrieved_docs, retrieved_metas)`

검색된 텍스트 Top-k를 로컬 LLM prompt에 넣을 하나의 문자열로 합친다.

각 문서 앞에 다음 출처 표시를 붙인다.

```text
[관련도 1순위 자료 | 출처: 제목 (페이지 ...)]
본문
```

문서와 메타데이터는 `zip()`으로 묶으므로 길이가 다르면 짧은 쪽까지만 사용한다.

## 5. 이미지 후보 기본 구조와 단계 문맥 읽기

### 5.1 `_candidate(candidates, file_name, image_path)`

#### 목적

여러 검색 경로에서 같은 이미지가 발견되어도 파일명 기준 하나의 후보로 합친다.

#### 처리

1. `resolve_image_path()`로 실제 경로 후보를 만든다.
2. 최종 파일명을 dictionary key로 사용한다.
3. 처음 발견된 이미지면 모든 점수를 0으로 초기화한 후보 딕셔너리를 만든다.
4. 기존 후보면 같은 딕셔너리를 반환한다.

후보에는 검색 신호, 단계 신호, 최종 점수, 출처 목록, 설명 필드가 포함된다.

### 5.2 `load_image_page_index()`

`final_processing_report.json`을 읽어 `{페이지: 이미지 목록}` 형태로 바꾼다.

`@lru_cache(maxsize=1)`이 적용되어 프로세스 안에서 한 번만 읽는다. 실행 중 JSON 파일이 바뀌어도 cache를 비우지 않으면 이전 결과를 계속 사용한다.

### 5.3 `_split_terms(value)`

CSV의 쉼표, 세미콜론, 슬래시, 세로줄 구분 문자열을 소문자 term 리스트로 나눈다. 빈 term과 중복 term은 제거한다.

### 5.4 `_parse_page_ranges(value)`

다음 형태의 페이지 문자열을 `(시작, 끝)` 튜플 리스트로 바꾼다.

- `10-15`
- `10;12;15`
- `15-10`: 자동으로 작은 수를 시작으로 정렬

범위가 아닌 항목에서는 모든 숫자를 찾아 단일 페이지 범위로 추가한다.

### 5.5 `_pages_from_ranges(ranges)`

페이지 범위 리스트를 실제 페이지 번호 집합으로 펼친다.

예: `[(3, 5), (8, 8)] -> {3, 4, 5, 8}`

### 5.6 `load_stage_context_map(map_path=None)`

#### 목적

단계 문맥 CSV를 검색에 바로 사용할 dictionary로 변환한다.

#### 입력 파일 인코딩

`utf-8-sig`를 사용하므로 Excel에서 만든 UTF-8 BOM CSV도 읽을 수 있다.

#### 각 단계에 저장하는 값

- `stage_id`
- 한글 실습 단계명
- 텍스트 페이지 범위
- 이미지 페이지 범위
- 섹션 키워드
- 본문 키워드
- 동작·질문 키워드
- 단계 가중치
- 매핑 근거

단계명이 비어 있는 행은 건너뛴다.

`@lru_cache(maxsize=8)`이 적용되어 경로별 결과가 cache된다.

### 5.7 `_stage_context_for(stage_label, map_path=None)`

1. 단계 label이 없으면 `None`
2. context map에서 정확히 같은 단계명 검색
3. 없으면 대소문자를 무시하고 다시 검색
4. 그래도 없으면 `None`

반환값이 `None`이면 G4가 적용되지 않는다.

### 5.8 `extract_pages(value)`

페이지 메타데이터를 정수 리스트로 바꾼다.

1. JSON list로 파싱되면 숫자로 보이는 항목만 정수화한다.
2. JSON list가 아니면 문자열에서 모든 숫자를 정규식으로 추출한다.

### 5.9 `image_page_from_name(value)`

`page_12_img_...` 형식의 이미지 이름에서 페이지 숫자를 추출한다. 형식이 맞지 않으면 `None`을 반환한다.

### 5.10 `candidate_pages(item)`

이미지 후보의 가능한 페이지 정보를 다음 세 곳에서 합친다.

- `item["page"]`
- `item["pages"]`
- 이미지 파일명

중복 없는 정수 집합을 반환한다.

### 5.11 `page_range_score(pages, ranges)`

후보 페이지가 단계 페이지 범위에 얼마나 가까운지 점수화한다.

| 관계 | 점수 |
|---|---:|
| 범위 안 | 1.00 |
| 범위에서 1페이지 차이 | 0.70 |
| 범위에서 2페이지 차이 | 0.45 |
| 그보다 멂 | 0 |

모든 페이지·범위 조합 중 가장 높은 값을 사용한다.

### 5.12 `term_match_score(terms, text, max_terms=8)`

단계 term이 후보 텍스트에 부분 문자열로 포함되는지 검사한다.

점수는 `매칭된 고유 term 수 / min(8, 전체 term 수)`이며 최대 1이다. 점수와 매칭 term 목록을 함께 반환한다.

형태소 분석이나 token 경계 비교가 아니라 단순 소문자 부분 문자열 비교이다.

## 6. G3 이미지 후보 수집 함수

### 6.1 `_add_text_image_candidates(candidates, metas)`

#### 후보 경로

상위 텍스트 청크의 `linked_images`에 전처리 시 연결된 이미지이다.

#### 처리

1. 텍스트 검색 순위를 0~1 `rank_score`로 바꾼다.
2. 청크의 `mapping_candidates`를 파일명 dictionary로 만든다.
3. 각 연결 이미지의 실제 파일 존재 여부를 확인한다.
4. 공통 후보 딕셔너리를 가져온다.
5. 제목, 페이지, 가장 높은 텍스트 순위 점수, 매핑 점수, 도면 점수를 반영한다.
6. `sources`에 `text_top_{순위}`를 기록한다.

같은 이미지가 여러 텍스트에서 발견되면 각 점수의 최댓값을 유지한다.

### 6.2 `_add_page_neighbor_candidates(candidates, metas)`

#### 후보 경로

상위 텍스트 청크와 같은 페이지 및 앞·뒤 한 페이지의 모든 최종 이미지이다.

#### 처리

1. 텍스트 청크 페이지마다 `-1, 0, +1` 페이지 후보를 만든다.
2. 같은 페이지면 multiplier 1.0, 인접 페이지면 0.82를 적용한다.
3. 텍스트 순위 점수와 multiplier로 `page_score`를 계산한다.
4. 도면 점수와 출처를 반영한다.

이 함수가 G3 기본 점수에서 가장 큰 가중치인 페이지 근접 신호를 제공한다.

### 6.3 `_add_image_collection_candidates(...)`

#### 후보 경로

이미지 전용 BGE-M3 collection의 질문 검색 결과이다.

#### 처리

1. 결과의 메타데이터, 거리, 문서를 첫 batch에서 꺼낸다.
2. 파일명이 없는 결과는 제외한다.
3. 거리를 `distance_to_score()`로 변환한다.
4. 이미지 파일 존재 여부를 확인한다.
5. 이미지 주변 제목과 페이지를 후보 설명에 반영한다.
6. 이미지 검색 점수와 도면 점수의 최댓값을 유지한다.
7. 검색 문서 앞 240자를 `document_preview`로 저장한다.

`source_prefix`와 `score_key` 매개변수로 출처명과 저장 점수 key를 바꿀 수 있지만 현재 기본값을 사용한다.

### 6.4 `_candidate_stage_text(item)`

단계 키워드 비교에 사용할 문자열을 만든다.

- 파일명
- 제목
- 페이지 문자열
- 단일 페이지
- 이미지 검색 문서 미리보기

모든 값을 공백으로 연결하고 소문자로 바꾼다.

## 7. G4 이미지 문맥 함수

### 7.1 `_add_stage_map_page_candidates(candidates, stage_context)`

#### 목적

G3 검색 경로에서 발견되지 않았더라도 추정 단계의 이미지 페이지 범위에 있는 이미지를 후보군에 추가한다.

#### 처리

1. 단계의 이미지 범위를 실제 페이지 집합으로 펼친다.
2. 각 페이지의 최종 이미지를 가져온다.
3. 파일이 존재하면 후보에 추가한다.
4. `stage_page_score=1.0`과 도면 점수, `stage_map_page` 출처를 기록한다.

질문 번호나 정답 파일명을 사용하지 않고 단계별 페이지 범위만 사용한다.

### 7.2 `_apply_stage_context(candidates, stage_label, stage_context=None)`

#### 목적

모든 이미지 후보에 단계 페이지·키워드·섹션 점수를 계산한다.

#### 계산

```text
stage_map_score =
  (0.50 × page_score
 + 0.10 × keyword_score
 + 0.40 × section_score)
 × stage_profile_weight
```

`keyword_terms`는 본문 키워드와 동작·질문 키워드를 합친다.

#### 설명 정보

점수뿐 아니라 다음 이유를 `stage_reason`에 기록한다.

- 페이지 점수
- 매칭 키워드 최대 4개
- 매칭 섹션 term 최대 3개

`stage_label` 인자는 현재 함수 내부 계산에 직접 사용되지 않고, 이미 선택된 `stage_context`가 실제 점수 기준이 된다.

### 7.3 `_base_image_score(item)`

G3의 다섯 신호를 고정 가중합하여 반환한다. 반올림은 이 함수가 아니라 `rank_image_candidates()`에서 수행한다.

### 7.4 `rank_image_candidates(candidates, limit=10, use_stage_context=False)`

#### 1단계: G3 기본 순위

모든 후보의 `base_score`를 계산하고 다음 tie-break 순서로 정렬한다.

1. 기본 점수
2. 이미지 검색 점수
3. 페이지 점수
4. 텍스트 순위 점수
5. 매핑 점수

정렬 결과를 `base_rank`에 기록한다.

#### 2단계: G4 rank factor

단계 문맥을 사용하면 다음 규칙을 적용한다.

- 기본 순위가 120 이내: 1에서 0 방향으로 선형 감소
- 120 밖이지만 단계 페이지 안: 0.35
- 나머지: 0

이는 기본 검색 근거가 약한 이미지가 단계 키워드만으로 과도하게 상승하는 것을 줄인다.

#### 3단계: 최종 점수

G4에서는 단계 점수와 페이지 prior를 더한다. G3에서는 기본 점수만 사용한다.

#### 4단계: 최종 정렬

최종 점수 이후 단계 점수, 단계 페이지 점수, G3의 개별 점수를 tie-break로 사용한다. 상위 `limit`개에 1부터 rank를 부여해 반환한다.

최종 점수는 여러 가산점으로 인해 1을 초과할 수 있다. 확률이 아니라 순위용 점수이다.

## 8. G4 텍스트 재순위화

### 8.1 `_text_stage_score(doc, meta, stage_context)`

#### 계산 대상

- 청크 페이지
- 제목
- 페이지 문자열
- 본문

#### 계산식

```text
text_stage_score =
  (0.55 × page_score
 + 0.30 × keyword_score
 + 0.15 × section_score)
 × stage_profile_weight
```

점수와 매칭 근거 문자열을 반환한다.

### 8.2 `rank_text_results(ids, docs, metas, limit, stage_context=None)`

#### G3 또는 단계 없음

입력 순서의 상위 `limit`개를 그대로 반환한다.

#### G4

1. 전체 후보 내 기존 순위를 1~0 방향의 `base_rank_score`로 바꾼다.
2. `_text_stage_score()`를 계산한다.
3. `score = base_rank_score + 0.28 × stage_score`를 계산한다.
4. G4 점수, 근거, 원래 순위를 복사한 메타데이터에 추가한다.
5. 최종 점수, 단계 점수, 기본 순위 점수 순으로 정렬한다.
6. 상위 `limit`개의 ID·문서·메타데이터를 각각 반환한다.

## 9. 최종 검색 함수

### 9.1 `retrieve_multimodal(...)`

#### 목적

사용자 질문 하나에 대한 텍스트 근거, LLM 문맥, 이미지 후보를 모두 만드는 공개 진입 함수이다.

#### 주요 매개변수

- `question`: 사용자 질문
- `embedder`: BGE-M3
- `text_collection`: 정확 검색 text wrapper
- `image_collection`: 정확 검색 image wrapper 또는 `None`
- 각 Top-k 값
- `stage_label`: G4에 사용할 단계 또는 `None`
- `stage_context_map_path`: 단계 문맥 CSV

#### 1단계: 질문 임베딩

BGE-M3로 질문을 한 번 임베딩하고 Python 리스트로 바꾼다. 텍스트와 이미지 전용 collection 검색에 같은 embedding을 사용한다.

#### 2단계: 단계 문맥 확인

`_stage_context_for()`로 단계 label에 해당하는 context를 찾는다.

- context 있음: G4
- context 없음: G3

#### 3단계: 답변용 텍스트 검색

- G3: 바로 Top-5 검색
- G4: Top-30을 검색한 뒤 단계 점수로 재순위화하여 Top-5 선택

선택된 Top-5로 `make_context()`를 호출한다.

#### 4단계: 이미지 후보용 텍스트 검색

텍스트 collection에서 별도로 Top-60을 검색한다. 이 결과로 다음 후보를 추가한다.

- 전처리에서 텍스트에 연결된 이미지
- 텍스트와 같은 페이지 및 인접 페이지 이미지

#### 5단계: 이미지 전용 검색

이미지 collection이 있으면 질문 embedding으로 Top-80을 검색하여 후보에 합친다.

#### 6단계: G4 후보 확장과 문맥 점수

단계 context가 있으면 다음을 추가한다.

1. 단계 이미지 페이지 범위의 이미지 후보
2. 모든 후보의 단계 페이지·키워드·섹션 점수

#### 7단계: 이미지 정렬

`rank_image_candidates()`로 G3 또는 G4 점수를 계산하고 Top-10을 선택한다.

#### 반환 딕셔너리

| key | 내용 |
|---|---|
| `query_embedding` | 질문 BGE-M3 임베딩 |
| `answer_ids` | 최종 텍스트 ID |
| `answer_docs` | 최종 텍스트 본문 |
| `answer_metas` | 최종 텍스트 메타데이터 |
| `context` | LLM prompt용 출처 포함 문자열 |
| `images` | 최종 이미지 후보 |
| `image_collection_available` | 이미지 collection 존재 여부 |
| `stage_context_used` | G4 적용 여부 |
| `stage_context_map_used` | 단계 context 발견 여부 |
| `stage_context` | 실제 사용 단계 설정 |

## 10. 전체 호출 흐름

```text
retrieve_multimodal()
  |- embedder.encode(question)
  |- _stage_context_for()
  |    `- load_stage_context_map()
  |- text_collection.query()
  |- rank_text_results()
  |    `- _text_stage_score()
  |- _add_text_image_candidates()
  |- _add_page_neighbor_candidates()
  |- image_collection.query()
  |- _add_image_collection_candidates()
  |- _add_stage_map_page_candidates()   # G4만
  |- _apply_stage_context()             # G4만
  |- rank_image_candidates()
  `- make_context()
```

## 11. 실행·수정 시 주의사항

1. 정확 검색은 결과 재현성에 유리하지만 데이터 전체 임베딩을 RAM에 올린다.
2. `load_image_page_index()`와 `load_stage_context_map()`은 cache되므로 실행 중 파일을 바꾸면 앱을 재시작하는 편이 안전하다.
3. G4 점수는 확률이 아니라 후보 순위를 위한 가산 점수이다.
4. 단계 문맥이 없거나 자동 분류가 기준을 통과하지 못하면 G3로 폴백한다.
5. 이미지 collection이 없어도 텍스트 연결·페이지 주변 이미지 검색은 작동한다.
6. `term_match_score()`는 단순 부분 문자열 검색이므로 동의어, 조사 변화, 형태 변화는 단계 profile에 직접 포함되지 않으면 놓칠 수 있다.
7. 가중치와 threshold는 현재 내부 70개 질의 기반 설정이며 다른 매뉴얼에 일반화가 검증된 상수는 아니다.

