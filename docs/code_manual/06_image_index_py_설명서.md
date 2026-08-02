# `src/image_index.py` 상세 설명서

## 1. 파일 역할

`image_index.py`는 이미지 자체의 pixel feature를 검색 DB에 넣는 파일이 아니다. 이미지 파일명, 페이지, 도면 점수, 주변 텍스트 청크를 하나의 설명 문서로 만든 뒤 BGE-M3 텍스트 임베딩으로 이미지 전용 검색 컬렉션을 구축한다.

사용자 질문도 BGE-M3로 임베딩되므로, 질문과 이미지 주변 설명 문서가 의미적으로 가까우면 해당 이미지가 후보에 들어온다.

## 2. 주요 상수

| 상수 | 값 | 의미 |
|---|---|---|
| `IMAGE_COLLECTION_NAME` | `doosan_image_collection` | 이미지 검색 컬렉션 이름 |
| `IMAGE_CONTEXT_CHUNKS` | 3 | 이미지마다 연결할 주변 텍스트 청크 수 |
| `IMAGE_TEXT_MAX_CHARS` | 180 | 주변 청크마다 문서에 넣을 본문 최대 길이 |
| `HNSW_CONFIGURATION` | sync threshold 100 | Chroma 저장 설정 |

## 3. 함수 설명

### 3.1 `_clean_text(value)`

#### 목적

메타데이터 문자열의 여러 공백과 줄바꿈을 한 칸으로 정리한다.

#### 반환

- `None`이나 빈 값은 빈 문자열
- 나머지는 공백이 정리된 문자열

함수명의 앞 `_`는 이 파일 내부에서 사용하는 보조 함수라는 관례를 나타낸다.

### 3.2 `_chunk_pages(chunk)`

#### 목적

청크의 `pages` 목록을 정수 리스트로 변환한다.

#### 전제

모든 페이지 값이 `int()`로 바꿀 수 있어야 한다. 잘못된 문자열이 포함되면 예외가 발생한다.

### 3.3 `_bbox_distance(chunk, image)`

#### 목적

하나의 이미지와 하나의 텍스트 청크 사이의 공간 거리를 계산한다.

#### 같은 페이지 BBox가 있을 때

1. 이미지 페이지와 같은 페이지에 속한 텍스트 BBox만 고른다.
2. 텍스트 BBox 전체를 감싸는 영역 중심을 계산한다.
3. 이미지 BBox 중심을 계산한다.
4. 두 중심 사이 유클리드 거리를 반환한다.

#### 같은 페이지 BBox가 없을 때

- 청크 페이지도 없으면 `99999.0`
- 청크 페이지가 있으면 이미지 페이지와 가장 가까운 페이지 차이 × 1000

페이지 차이가 BBox 픽셀 거리보다 훨씬 크게 반영되도록 만든 폴백이다.

### 3.4 `_related_chunks_for_image(image, text_chunks)`

#### 목적

각 이미지와 공간적으로 가까운 텍스트 청크 3개를 찾는다.

#### 처리

1. 모든 텍스트 청크를 순회한다.
2. 이미지 페이지와 청크 페이지의 최소 차이를 구한다.
3. 페이지 차이가 1보다 크면 제외한다.
4. `_bbox_distance()`를 계산한다.
5. `페이지 차이 × 1000 + BBox 거리`를 최종 근접 점수로 사용한다.
6. 점수가 작은 순으로 정렬해 상위 3개를 반환한다.

#### 반환 구조

```text
(근접 점수, 원본 chunk 인덱스, chunk 딕셔너리)
```

### 3.5 `_build_image_document(image, related_chunks)`

#### 목적

이미지 하나를 BGE-M3로 검색할 수 있는 텍스트 문서로 표현한다.

#### 기본 문서 내용

- 이미지 파일명
- 매뉴얼 페이지
- 이미지 추출 단계의 도면 신뢰도

#### 주변 텍스트 내용

각 근접 청크에 대해 다음을 추가한다.

- 근접 순위
- `chunk_{번호}`
- 청크 페이지
- 제목
- 공백 정리 후 앞 180자의 본문

#### 반환

줄바꿈으로 연결한 하나의 문자열

### 3.6 `build_image_search_collection(...)`

#### 목적

모든 최종 이미지를 ChromaDB 이미지 전용 컬렉션에 저장한다.

#### 매개변수

- `text_chunks`: 텍스트 청크 리스트
- `image_metadata`: 최종 이미지 메타데이터
- `embedding_model`: BGE-M3 SentenceTransformer
- `client`: ChromaDB client
- `reset`: 기존 이미지 컬렉션 삭제 여부, 기본값 `True`

#### 1단계: 컬렉션 준비

`reset=True`이면 기존 `doosan_image_collection`을 삭제한다. 컬렉션이 없어 발생하는 예외는 무시한다. 이후 새 컬렉션을 가져오거나 생성한다.

#### 2단계: 이미지별 검색 문서 생성

각 이미지마다 다음을 수행한다.

1. 실제 이미지 파일 존재 여부를 확인한다.
2. `_related_chunks_for_image()`로 주변 텍스트 3개를 찾는다.
3. `_build_image_document()`로 검색 문서를 만든다.
4. 이미지 ID, 문서, 메타데이터를 목록에 추가한다.

#### 이미지 ID

```text
image_{확장자를 제외한 파일명}
```

#### 저장 메타데이터

- `file_name`
- 이미지 페이지
- 프로젝트 상대 이미지 경로
- 도면 SigLIP 점수
- 연결 텍스트 chunk ID JSON
- 연결 제목 JSON
- 연결 페이지 JSON

#### 3단계: 임베딩과 저장

1. 모든 이미지 설명 문서를 BGE-M3로 batch 32 임베딩한다.
2. 50개 단위로 ChromaDB에 `upsert()`한다.
3. 완성된 collection 객체를 반환한다.

## 4. 호출 관계

```text
embedding_text_image.build_multimodal_db_v2()
        `- image_index.build_image_search_collection()
                `- doosan_image_collection

rag_search.retrieve_multimodal()
        `- doosan_image_collection 정확 벡터 검색
```

## 5. 이미지 검색에서의 의미

이 컬렉션은 다음 경로로 이미지 후보를 보완한다.

1. 질문을 BGE-M3로 임베딩한다.
2. 이미지 설명 문서 임베딩과 비교한다.
3. 질문과 의미적으로 가까운 주변 텍스트를 가진 이미지를 찾는다.
4. 이 결과를 텍스트 연결 이미지와 페이지 주변 이미지 후보에 합친다.

따라서 이 컬렉션은 SigLIP의 pixel-text 유사도와 다른 신호를 제공한다. SigLIP 매핑은 전처리 청크와 이미지 의미 관계를 저장하고, 이미지 전용 컬렉션은 사용자 질문과 이미지 주변 텍스트 관계를 검색한다.

## 6. 주의사항

1. 실제 이미지 파일이 없으면 해당 메타데이터는 컬렉션에서 제외된다.
2. 주변 청크는 최대 3개이며 본문은 각각 180자로 잘린다.
3. BBox가 잘못되면 이미지 설명에 연결되는 청크 품질도 낮아질 수 있다.
4. `documents`가 빈 리스트이면 `embedding_model.encode()`와 컬렉션 구축 흐름을 별도로 확인해야 한다.
5. 이미지 pixel을 직접 BGE-M3에 넣지 않는다는 점을 문서나 발표에서 명확히 구분해야 한다.

