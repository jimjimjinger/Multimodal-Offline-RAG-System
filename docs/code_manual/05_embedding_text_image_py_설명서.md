# `src/embedding_text_image.py` 상세 설명서

## 1. 파일 역할

`embedding_text_image.py`는 이미지 전처리 결과와 텍스트 청킹 결과를 하나의 멀티모달 검색 DB로 결합한다.

핵심 작업은 다음과 같다.

1. BGE-M3로 텍스트 청크 임베딩 생성
2. SigLIP 이미지 feature 사전 계산
3. 각 텍스트 청크에 대해 같은 페이지와 다음 페이지 이미지 후보 수집
4. BBox 거리로 공간 후보 제한
5. SigLIP cosine 유사도로 후보 의미 순위 결정
6. 텍스트 컬렉션과 이미지 전용 컬렉션을 ChromaDB에 저장

앱 실행 시에는 이 무거운 SigLIP 계산을 반복하지 않는다. 계산 결과를 메타데이터와 DB에 저장해 두고 검색 단계에서 재사용한다.

## 2. 입력과 출력

### 입력

| 경로 | 내용 |
|---|---|
| `data/processed/text_chunks.json` | 텍스트, 제목, 페이지, 텍스트 BBox |
| `data/processed/final_processing_report.json` | 이미지 파일명, 페이지, 이미지 BBox, 도면 점수 |
| `data/processed/final_refined_data/` | 실제 이미지 파일 |
| `models/siglip_local/` | 로컬 SigLIP processor와 model |

### 출력

| 경로 | 내용 |
|---|---|
| `data/vector_db/rag_db/` | ChromaDB 텍스트·이미지 컬렉션 |
| `data/processed/text_image_mapping_report.json` | 청크별 이미지 연결 상세 기록 |

## 3. 주요 상수

### 3.1 컬렉션과 장치

| 상수 | 값 | 의미 |
|---|---|---|
| `DEVICE` | CUDA 가능 시 `cuda`, 아니면 `cpu` | SigLIP 계산 장치 |
| `COLLECTION_NAME` | `doosan_manual_collection` | 텍스트 컬렉션 |
| `HNSW_CONFIGURATION` | sync threshold 100 | Chroma 저장 컬렉션 설정 |

Chroma는 HNSW 기반 컬렉션으로 데이터를 저장하지만, 현재 앱의 `rag_search.ExactVectorCollection`은 저장된 임베딩 전체를 읽고 정확 전수 검색을 수행한다.

### 3.2 이미지 매핑 기준

| 상수 | 값 | 의미 |
|---|---:|---|
| `MAX_DISTANCE` | 300 | BBox 공간 후보 거리 기준 |
| `TOP_N_IMAGES` | 2 | 청크마다 저장할 최대 연결 이미지 수 |
| `SIGLIP_KEEP_THRESHOLD` | 0.40 | 멀리 있어도 유지할 SigLIP 정규화 점수 |
| `SIGLIP_TEXT_MAX_CHARS` | 1200 | SigLIP 입력 텍스트 최대 길이 |
| `SIGLIP_IMAGE_BATCH_SIZE` | 16 | 이미지 feature 계산 batch |

### 3.3 SigLIP cosine 정규화 범위

`SIGLIP_COSINE_LOW`와 `SIGLIP_COSINE_HIGH`는 동일·인접 페이지에서 수집한 985개 쌍의 cosine 5·95 percentile을 사용한다.

```text
LOW  = -0.03492925
HIGH =  0.09054340
```

이 구간 아래는 0, 위는 1로 잘라 검색 점수 범위로 사용한다.

## 4. 함수 설명

### 4.1 `calculate_2d_distance(text_bboxes, img_bbox)`

#### 목적

텍스트 청크 전체 영역의 중심과 이미지 BBox 중심 사이의 2차원 유클리드 거리를 계산한다.

#### 입력

- `text_bboxes`: `{"page": ..., "coord": [x0, y0, x1, y1]}` 리스트
- `img_bbox`: `{"x0": ..., "y0": ..., "x1": ..., "y1": ...}`

#### 처리

1. 텍스트 BBox 전체의 최소 x·y와 최대 x·y를 구해 하나의 포괄 영역을 만든다.
2. 포괄 텍스트 영역의 중심점을 계산한다.
3. 이미지 영역의 중심점을 계산한다.
4. `math.hypot()`으로 두 중심점 거리를 구한다.
5. 이미지 중심이 텍스트 중심 아래에 있으면 거리에 0.8을 곱한다.

그림이 설명 텍스트 아래에 배치되는 일반적인 매뉴얼 구조를 반영한 휴리스틱이다.

#### 반환

- 계산된 거리
- 텍스트 BBox가 없으면 `9999.0`

### 4.2 `check_explicit_caption(text)`

#### 목적

본문에 `그림 1`, `도면 2`, `Fig. 3`, `Figure 4`처럼 숫자가 포함된 명시적 그림 참조가 있는지 찾는다.

#### 반환

- 정규식이 발견되면 `True`
- 그렇지 않으면 `False`

현재 코드는 특정 그림 번호와 파일명을 직접 연결하지 않는다. 명시적 참조가 있으면 해당 청크의 이미지 거리 전체에 0.1을 곱해 공간 후보가 더 쉽게 남도록 만든다.

### 4.3 `build_siglip_text_prompt(chunk)`

#### 목적

SigLIP 텍스트 encoder에 넣을 청크 설명을 만든다.

#### 처리

1. 본문과 제목의 연속 공백을 한 칸으로 줄인다.
2. 제목이 있으면 `제목. 본문` 형태로 합친다.
3. 앞에서 최대 1200자까지만 반환한다.

긴 청크가 모델 입력을 지나치게 늘리는 것을 제한한다.

### 4.4 `load_siglip_resources()`

#### 목적

로컬 SigLIP processor와 model을 준비한다.

#### 처리

1. `models/siglip_local` 존재 여부를 확인한다.
2. 없으면 `scripts/download_siglip.py` 실행 안내가 포함된 `FileNotFoundError`를 발생시킨다.
3. processor와 model을 로컬 경로에서 읽는다.
4. 모델을 `DEVICE`로 이동한다.
5. `model.eval()`로 평가 모드를 활성화한다.

#### 반환

`(processor, model)` 튜플

### 4.5 `extract_feature_tensor(features)`

#### 목적

Transformers 버전에 따라 달라질 수 있는 SigLIP feature 반환 형식을 하나의 2차원 tensor로 통일한다.

#### 처리 순서

1. 이미 `torch.Tensor`이면 그대로 반환한다.
2. `pooler_output`이 있으면 해당 값을 반환한다.
3. `last_hidden_state`가 있으면 첫 token feature인 `[:, 0]`을 반환한다.
4. 모두 아니면 `TypeError`를 발생시킨다.

### 4.6 `precompute_siglip_image_features(img_metadata, processor, model)`

#### 목적

각 텍스트 청크마다 이미지를 반복 인코딩하지 않도록 모든 이미지 feature를 한 번만 계산해 메모리에 저장한다.

#### 내부 함수 `flush_batch()`

`precompute_siglip_image_features()` 안에 정의된 지역 함수이다.

1. 현재 batch에 이미지가 없으면 즉시 반환한다.
2. processor로 이미지 tensor를 만든다.
3. `model.get_image_features()`로 feature를 얻는다.
4. `extract_feature_tensor()`로 형식을 통일한다.
5. L2 정규화하고 CPU로 옮긴다.
6. 파일명을 key로 feature를 딕셔너리에 저장한다.
7. batch 목록을 비운다.

#### 외부 반복

1. 메타데이터의 각 파일명을 실제 이미지 경로와 결합한다.
2. 파일이 없으면 건너뛴다.
3. RGB 이미지로 열어 batch에 추가한다.
4. 16개가 모이면 `flush_batch()`를 호출한다.
5. 반복 종료 후 남은 batch도 처리한다.

#### 반환

`{파일명: 정규화된 이미지 feature tensor}` 딕셔너리

### 4.7 `calculate_siglip_image_text_scores(...)`

#### 목적

하나의 텍스트 prompt와 여러 이미지 후보 사이의 SigLIP 의미 유사도를 계산한다.

#### 입력

- `text_prompt`: 제목과 본문을 합친 텍스트
- `candidates`: 이미지 후보 딕셔너리 리스트
- `processor`, `model`: SigLIP 자원
- `image_features`: 사전 계산한 이미지 feature

#### 누락 이미지 처리

feature가 없는 후보에는 다음 값을 기록하고 계산 대상에서 제외한다.

- cosine과 similarity 0
- `image_missing=True`

#### 텍스트 feature 계산

1. 텍스트 하나를 processor에 넣는다.
2. `model.get_text_features()`를 호출한다.
3. 반환 형식을 통일하고 L2 정규화한다.
4. CPU의 1차원 feature로 만든다.

#### 유사도 계산

1. 이미지 feature를 하나의 matrix로 쌓는다.
2. matrix와 텍스트 feature를 내적해 cosine 점수를 얻는다.
3. 모델에 `logit_scale`이 있으면 지수 값을 곱한다.
4. `logit_bias`가 있으면 더한다.
5. 각 logit에 sigmoid를 적용해 pair probability를 기록한다.
6. 실제 검색 매핑 점수는 raw probability가 아니라 `normalize_siglip_cosine()` 결과를 사용한다.

#### 후보에 저장되는 값

- `siglip_cosine`: 정규화 전 cosine
- `siglip_raw_logit`: scale과 bias 적용값
- `siglip_probability`: sigmoid 결과
- `image_text_similarity`: percentile 범위로 0~1 정규화한 cosine
- `image_missing`: feature 누락 여부

### 4.8 `calculate_distance_score(distance)`

#### 목적

BBox 거리를 0~1 점수로 바꿔 분석 메타데이터에 기록한다.

#### 계산

- 거리가 300 이상이면 0
- 그보다 작으면 `1 - distance / 300`

현재 최종 `mapping_score`에는 이 점수가 직접 더해지지 않는다. 공간 후보 판단과 분석 정보로 사용한다.

### 4.9 `normalize_siglip_cosine(cosine)`

#### 목적

cosine을 데이터 기반 범위로 0~1 선형 정규화한다.

#### 계산

```text
(cosine - LOW) / (HIGH - LOW)
```

결과는 0과 1 사이로 제한한다. 구간 폭이 0 이하이면 0을 반환한다.

### 4.10 `build_multimodal_db_v2(...)`

#### 목적

이 파일의 전체 DB 구축 과정을 실행하는 메인 함수이다.

#### 매개변수

- `text_json`: 텍스트 청크 JSON, 기본값 `TEXT_CHUNKS_PATH`
- `img_json`: 이미지 메타데이터 JSON, 기본값 `FINAL_PROCESSING_REPORT_PATH`
- `db_path`: ChromaDB 위치, 기본값 `VECTOR_DB_DIR`

#### 1단계: 데이터와 DB 준비

1. 텍스트와 이미지 JSON을 읽는다.
2. Hugging Face 캐시를 설정한다.
3. ChromaDB 부모 폴더를 만든다.
4. `PersistentClient`를 연다.
5. 기존 텍스트 컬렉션이 있으면 삭제한다.
6. 새 `doosan_manual_collection`을 만든다.

기존 컬렉션 삭제 예외는 무시한다. 컬렉션이 원래 없을 때도 계속 진행하기 위한 처리이다.

#### 2단계: 모델 feature 준비

1. BGE-M3를 불러온다.
2. 모든 텍스트 청크 본문을 batch 32로 임베딩한다.
3. SigLIP processor와 model을 불러온다.
4. 모든 이미지 feature를 사전 계산한다.

#### 3단계: 청크별 이미지 후보 수집

각 텍스트 청크마다 다음을 수행한다.

1. 청크의 첫 페이지를 기준 페이지로 사용한다.
2. 같은 페이지와 다음 페이지의 이미지를 후보로 수집한다.
3. 명시적 그림 참조 여부를 검사한다.
4. SigLIP 입력 prompt를 만든다.
5. 각 후보의 BBox 거리를 계산한다.
6. 다음 페이지 이미지는 거리에 1000을 더한다.
7. 청크에 그림 참조가 있으면 최종 거리에 0.1을 곱한다.
8. 거리 점수와 이미지 추출 단계의 도면 SigLIP 점수를 후보에 기록한다.

#### 4단계: SigLIP 의미 점수

`calculate_siglip_image_text_scores()`로 후보 전체의 cosine, logit, sigmoid probability, 정규화 cosine을 계산한다.

최종 매핑 점수는 다음과 같이 설정된다.

```python
mapping_score = image_text_similarity
```

BBox 거리 점수는 최종 의미 순위에 가중합으로 직접 포함되지 않는다.

#### 5단계: 후보 필터와 Top-2

다음 중 하나라도 만족하면 후보를 유지한다.

- BBox 거리가 300 미만
- 정규화 SigLIP 유사도가 0.40 이상

유지 후보는 `mapping_score` 내림차순으로 정렬한다. 점수가 같으면 거리가 가까운 후보가 먼저 온다. 상위 2개만 청크에 연결한다.

#### 6단계: 텍스트 컬렉션 메타데이터

각 청크에는 다음 정보가 저장된다.

- 제목과 페이지
- 연결 이미지 상대 경로 JSON
- 대표 이미지 도면 점수
- 대표 이미지 텍스트 유사도
- 대표 매핑 점수
- Top 후보별 거리·cosine·probability·도면 점수
- 매핑 방법 이름

텍스트 본문, BGE 임베딩, 메타데이터, `chunk_{번호}` ID를 ChromaDB에 `upsert()`한다.

#### 7단계: 매핑 보고서 저장

청크 ID, 제목, 페이지, 텍스트 미리보기, 연결 이미지, 후보 상세를 `text_image_mapping_report.json`에 저장한다.

#### 8단계: 이미지 전용 컬렉션

`build_image_search_collection()`을 호출한다. 이 함수는 `image_index.py`에 정의되어 있으며, 이미지 주변 텍스트를 하나의 검색 문서로 만들어 BGE-M3 임베딩을 저장한다.

## 5. 메인 실행부

```python
if __name__ == "__main__":
    build_multimodal_db_v2()
```

직접 실행하면 기본 경로를 사용해 DB 전체를 다시 만든다.

## 6. 점수 역할 구분

| 값 | 계산 위치 | 최종 역할 |
|---|---|---|
| 이미지 `siglip_score` | 이미지 추출 | 도면다운 이미지인지 판단 |
| BBox `distance` | 텍스트-이미지 매핑 | 공간 후보 제한 |
| `distance_score` | 텍스트-이미지 매핑 | 분석 메타데이터 |
| `siglip_cosine` | 텍스트-이미지 매핑 | 원본 의미 유사도 |
| `siglip_probability` | 텍스트-이미지 매핑 | SigLIP logit의 pair probability 기록 |
| `image_text_similarity` | 텍스트-이미지 매핑 | cosine을 0~1로 정규화한 순위 점수 |
| `mapping_score` | 텍스트-이미지 매핑 | 현재 `image_text_similarity`와 동일 |

## 7. 재실행 시 주의사항

1. 이 함수를 실행하면 기존 텍스트·이미지 컬렉션이 재구축된다.
2. 원본 이미지나 청크 JSON이 누락되면 완전한 DB가 만들어지지 않는다.
3. CUDA는 SigLIP feature 계산을 빠르게 하지만 BGE-M3의 실제 장치는 SentenceTransformer 설정과 환경에 따라 결정된다.
4. `page_num = chunk["pages"][0]`이므로 페이지 리스트가 비어 있으면 오류가 발생한다.
5. SigLIP percentile 상수는 현재 데이터 분포에서 얻은 값이므로 다른 매뉴얼에 그대로 적용할 때 재검토해야 한다.
6. 처리 중 중단되면 부분 컬렉션이 남을 수 있다.

