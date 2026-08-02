# `src/text_filter.py` 상세 설명서

## 1. 파일 역할

`text_filter.py`는 PDF의 텍스트를 추출하여 제목 단위의 물리 청크를 만든 뒤, BGE-M3 임베딩으로 연속 문장 사이 의미 유사도를 계산해 의미 단위 청크로 다시 나눈다.

각 청크에는 본문뿐 아니라 페이지 번호와 PDF 좌표 BBox가 포함된다. 이 좌표는 이후 이미지와 가까운 텍스트를 찾는 공간 후보 필터에 사용된다.

## 2. 입력과 출력

### 입력

- `data/raw/A-Series.pdf`
- BGE-M3 모델 또는 로컬 Hugging Face 캐시

### 출력

- `data/processed/text_chunks.json`

### 최종 청크 구조

```json
{
  "heading": "Robot Installation",
  "text": "본문 내용 ...",
  "pages": [12, 13],
  "bboxes": [
    {"page": 12, "coord": [72.1, 153.0, 410.8, 167.2]}
  ]
}
```

## 3. 함수 설명

### 3.1 `get_physical_chunks(pdf_path)`

#### 목적

PDF 텍스트 span을 읽고 큰 제목을 경계로 물리 청크를 만든다. 본문 span의 페이지와 좌표도 함께 보존한다.

#### 입력과 반환

- `pdf_path`: PDF 파일 경로
- 반환: 물리 청크 딕셔너리 리스트

#### 내부 상태

- `current_heading`: 현재 청크의 제목
- `current_body_texts`: 현재 제목 아래 본문 span
- `current_pages`: 본문이 위치한 페이지 집합
- `current_bboxes`: 본문 span의 페이지와 좌표
- `current_span_bbox_pairs`: span 텍스트와 BBox의 쌍

`span_bbox_pairs`는 의미 청킹 후 각 문장에 대응하는 BBox만 골라내는 중간 정보이다.

#### 헤더와 푸터 제거

`HEADER_Y=50`, `FOOTER_Y=780`을 사용한다. span의 위쪽 좌표 `y0`가 50보다 작거나 780보다 크면 페이지 머리말·꼬리말 노이즈로 보고 제외한다.

이 값은 현재 PDF 페이지 크기를 가정한 고정 기준이다.

#### 제목 감지

다음 조건 중 하나를 만족하면 제목으로 본다.

1. 글자 크기가 14보다 큼
2. 글자 크기가 12보다 크고 `flags`의 굵은 글씨 비트가 설정됨

새 제목을 만나면 이전 본문이 존재할 경우 물리 청크로 저장한 뒤 상태를 초기화한다.

#### 본문 저장

제목이 아닌 span은 다음 정보로 누적한다.

- 공백 제거된 텍스트
- 1부터 시작하는 페이지 번호
- 소수점 둘째 자리로 반올림한 `[x0, y0, x1, y1]`
- `(span_text, bbox_record)` 쌍

PDF 전체 순회가 끝난 뒤 마지막 청크도 추가한다.

### 3.2 `find_bboxes_for_sentence(sentence, span_bbox_pairs, used_indices)`

#### 목적

의미 청킹에서 생성한 문장에 실제로 포함된 원본 span을 찾고 해당 BBox를 반환한다.

#### 입력

- `sentence`: 문장 문자열
- `span_bbox_pairs`: `(span_text, bbox)` 리스트
- `used_indices`: 이미 다른 문장에 할당된 span 인덱스 집합

#### 처리

1. 모든 span을 순서대로 본다.
2. 이미 사용된 인덱스는 건너뛴다.
3. `span_text in sentence`이면 해당 BBox를 결과에 추가한다.
4. 같은 span이 다음 문장에 중복 배정되지 않도록 인덱스를 `used_indices`에 넣는다.

#### 반환

매칭된 BBox 딕셔너리 리스트를 반환한다.

문장 분리 과정에서 원본 span 경계가 크게 바뀌거나 같은 짧은 문구가 반복되면 정확한 매칭이 어려울 수 있다.

### 3.3 `semantic_chunking(physical_chunks, model, similarity_threshold=0.5)`

#### 목적

제목 단위로 모인 긴 본문을 연속 문장 간 의미 유사도에 따라 더 작은 청크로 분리한다.

#### 입력

- `physical_chunks`: `get_physical_chunks()` 결과
- `model`: `SentenceTransformer` 호환 임베딩 모델
- `similarity_threshold`: 청크를 나누는 유사도 기준

#### 문장 분리

정규식 `(?<=[.!?])\s+`를 사용해 마침표, 느낌표, 물음표 뒤 공백에서 나눈다. 길이가 5 이하인 문자열은 제외한다.

영문 문장에는 일반적으로 적용되지만, 마침표 뒤 공백이 없는 텍스트나 PDF에서 단어가 잘못 결합된 경우 긴 문장으로 남을 수 있다.

#### 임베딩과 경계 결정

1. 청크의 모든 문장을 `model.encode(sentences)`로 임베딩한다.
2. 첫 문장부터 현재 의미 그룹을 시작한다.
3. 이전 문장 임베딩과 현재 문장 임베딩의 cosine 유사도를 계산한다.
4. 유사도가 임계값보다 낮으면 주제가 바뀐 것으로 보고 직전 그룹을 저장한다.
5. 임계값 이상이면 현재 그룹에 문장을 이어 붙인다.

현재 메인 실행부는 기본값 0.5가 아니라 `similarity_threshold=0.4`를 명시한다.

#### BBox 상속

각 문장을 처리할 때 `find_bboxes_for_sentence()`를 호출한다. 그룹에 매칭된 BBox가 있으면 해당 BBox와 페이지를 사용한다.

매칭된 BBox가 하나도 없으면 물리 청크 전체의 BBox와 페이지를 폴백으로 사용한다. 이 폴백은 좌표 정보 누락을 막지만 실제 문장보다 넓은 영역이 배정될 수 있다.

#### 반환

`heading`, `text`, `pages`, `bboxes`를 가진 최종 의미 청크 리스트를 반환한다.

## 4. 메인 실행부

### 4.1 모델 캐시 설정

`configure_model_cache()`를 호출해 Hugging Face 캐시를 프로젝트 내부로 지정한다.

### 4.2 BGE-M3 로드

```python
bge_m3_model = SentenceTransformer("BAAI/bge-m3")
```

BGE-M3는 다음 두 용도로 이어서 사용된다.

- 전처리 단계: 문장 경계 결정을 위한 의미 유사도
- DB 구축·검색 단계: 텍스트와 이미지 설명 문서의 검색 임베딩

### 4.3 청킹 실행

1. `get_physical_chunks(pdf_path)`
2. `semantic_chunking(..., similarity_threshold=0.4)`
3. 저장용 딕셔너리에서 내부용 `span_bbox_pairs` 제외
4. UTF-8 JSON 저장

### 4.4 결과 확인 출력

최종 청크 수와 첫 번째 청크의 제목, 페이지, 텍스트 일부를 터미널에 출력한다. 청크가 없으면 별도 메시지를 출력한다.

## 5. 다른 코드와의 연결

```text
text_filter.py
  `- text_chunks.json
       |- embedding_text_image.py: 텍스트 임베딩과 이미지 매핑
       `- image_index.py: 이미지 주변 텍스트 문서 생성
```

## 6. 재실행 및 조정 시 주의사항

1. 제목 판정의 글자 크기와 굵기 기준은 PDF 디자인에 종속된다.
2. 헤더·푸터 Y 좌표도 다른 페이지 크기의 PDF에서는 다시 조정해야 한다.
3. 유사도 임계값을 낮추면 더 많은 문장이 하나의 청크로 합쳐지고, 높이면 더 잘게 나뉜다.
4. `pages`는 집합에서 리스트로 바꾸므로 저장 전 정렬을 명시하지 않는다. 현재 데이터에서는 사용 가능하지만 항상 오름차순이라는 보장은 코드상 없다.
5. 이 파일을 다시 실행한 뒤에는 텍스트-이미지 매핑과 ChromaDB도 다시 구축해야 변경 결과가 앱에 반영된다.

