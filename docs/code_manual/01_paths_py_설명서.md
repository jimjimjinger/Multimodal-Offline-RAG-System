# `src/paths.py` 상세 설명서

## 1. 파일 역할

`paths.py`는 프로젝트에서 사용하는 파일과 폴더 경로를 한곳에 정의한다. 다른 코드가 현재 작업 폴더에 의존하지 않고 항상 프로젝트 루트를 기준으로 파일을 찾게 만드는 공통 모듈이다.

예를 들어 `text_filter.py`는 PDF 경로를 직접 문자열로 작성하지 않고 `A_SERIES_PDF`를 가져온다. 폴더 구조가 바뀌면 이 파일의 경로 정의를 중심으로 수정할 수 있다.

## 2. 프로젝트 루트 계산

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

1. `__file__`은 현재 파일인 `src/paths.py`를 가리킨다.
2. `resolve()`는 절대 경로로 변환한다.
3. `parents[1]`은 `src`의 한 단계 위인 프로젝트 루트를 선택한다.

따라서 터미널을 어느 폴더에서 실행하더라도 데이터 경로는 같은 위치를 가리킨다.

## 3. 주요 경로 상수

### 3.1 데이터 경로

| 상수 | 실제 위치 | 용도 |
|---|---|---|
| `DATA_DIR` | `data/` | 데이터 최상위 폴더 |
| `RAW_DATA_DIR` | `data/raw/` | 원본 PDF |
| `PROCESSED_DATA_DIR` | `data/processed/` | 전처리 결과 |
| `EVALUATION_DATA_DIR` | `data/evaluation/` | 평가 데이터 |
| `VECTOR_DB_DIR` | `data/vector_db/rag_db/` | ChromaDB 영구 저장소 |
| `FINAL_IMAGES_DIR` | `data/processed/final_refined_data/` | 최종 이미지 |
| `TEXT_CHUNKS_PATH` | `data/processed/text_chunks.json` | 텍스트 청크 |
| `FINAL_PROCESSING_REPORT_PATH` | `data/processed/final_processing_report.json` | 최종 이미지 메타데이터 |
| `TEXT_IMAGE_MAPPING_REPORT_PATH` | `data/processed/text_image_mapping_report.json` | 텍스트-이미지 연결 결과 |
| `A_SERIES_PDF` | `data/raw/A-Series.pdf` | 전처리 대상 PDF |

`PROCESSING_REPORT_PATH`도 이전 또는 중간 처리 보고서 경로로 정의되어 있지만 현재 핵심 실행 코드에서는 `FINAL_PROCESSING_REPORT_PATH`를 주로 사용한다.

### 3.2 모델 경로

| 상수 | 실제 위치 | 용도 |
|---|---|---|
| `MODELS_DIR` | `models/` | 모델 관련 파일 |
| `SIGLIP_MODEL_DIR` | `models/siglip_local/` | 로컬 SigLIP 모델 |
| `HF_CACHE_DIR` | `models/hf_cache/` | Hugging Face 캐시 |

### 3.3 SCIE 실험 경로

`SCIE_DIR`는 이름이 `SCIE`로 시작하는 폴더를 프로젝트 루트에서 찾는다. 운영체제나 터미널 인코딩에 따라 한글 폴더명을 직접 고정하지 않도록 한 처리이다.

| 상수 | 용도 |
|---|---|
| `SCIE_DATA_DIR` | CSV, JSON 등 연구 데이터 |
| `SCIE_EXCEL_DIR` | 연구용 Excel 파일 |
| `STAGE_CONTEXT_MAP_PATH` | 초기 단계 문맥표 |
| `STAGE_CONTEXT_MAP_MANUAL_PATH` | 최종 수동 검토 단계 문맥표 |

### 3.4 Ollama 경로

`OLLAMA_EXE`, `OLLAMA_HOME`, `OLLAMA_MODELS`는 프로젝트 내부 Ollama 실행 파일, 홈, 모델 저장 위치를 정의한다. 현재 Python 앱은 HTTP로 Ollama 서버에 접속하며, 이 경로들은 주로 실행 스크립트와 환경 구성에서 사용된다.

## 4. 함수 설명

### 4.1 `configure_model_cache()`

#### 목적

Hugging Face와 Transformers가 모델 캐시를 프로젝트의 `models/hf_cache` 아래에 저장하도록 환경 변수를 설정한다.

#### 입력과 반환

- 입력: 없음
- 반환: 없음
- 부수 효과: 현재 Python 프로세스의 환경 변수 변경

#### 내부 처리

1. `HF_HOME`을 `HF_CACHE_DIR`로 설정한다.
2. `TRANSFORMERS_CACHE`를 `HF_CACHE_DIR/transformers`로 설정한다.
3. `HF_HUB_DISABLE_SYMLINKS_WARNING`이 기존에 없을 때만 `1`로 설정한다.

`os.environ.setdefault()`를 사용한 마지막 설정은 사용자가 이미 지정한 값을 덮어쓰지 않는다.

#### 호출 위치

- `text_filter.py`
- `embedding_text_image.py`
- `app_runtime.py`

모델을 불러오기 전에 호출해야 캐시 경로가 반영된다.

### 4.2 `ensure_parent_dir(path)`

#### 목적

파일을 저장하기 전에 부모 폴더를 생성한다.

#### 입력과 반환

- `path`: 생성할 파일의 예상 경로
- 반환: 없음

#### 내부 처리

`Path(path).parent.mkdir(parents=True, exist_ok=True)`를 호출한다. 중간 폴더가 없어도 모두 생성하며, 이미 존재해도 오류를 내지 않는다.

### 4.3 `project_relative(path)`

#### 목적

절대 경로를 프로젝트 루트 기준 상대 경로로 바꿔 DB 메타데이터에 저장하기 쉽게 만든다.

#### 입력과 반환

- `path`: 프로젝트 내부의 파일 또는 폴더 경로
- 반환: `/` 구분자를 사용하는 문자열

#### 예시

```text
C:\project\data\processed\final_refined_data\page_10_img_2.png
-> data/processed/final_refined_data/page_10_img_2.png
```

입력 경로가 프로젝트 바깥에 있으면 `relative_to(PROJECT_ROOT)`에서 `ValueError`가 발생한다.

### 4.4 `resolve_image_path(image_path)`

#### 목적

DB에 저장된 이미지 경로가 절대 경로인지, 프로젝트 상대 경로인지, 파일명만 있는지에 관계없이 실제 파일 위치를 찾는다.

#### 검색 순서

입력이 절대 경로라면 해당 경로만 검사한다. 상대 경로라면 다음 순서로 후보를 만든다.

1. `PROJECT_ROOT / image_path`
2. `PROCESSED_DATA_DIR / image_path`
3. `FINAL_IMAGES_DIR / 입력 파일명`

첫 번째로 존재하는 경로를 반환한다.

#### 파일이 없을 때

어떤 후보도 존재하지 않으면 마지막 후보 경로를 반환한다. 즉, 함수가 반환했다고 해서 파일 존재가 보장되는 것은 아니다. 호출부에서 `exists()`를 추가 확인해야 한다.

## 5. 호출 관계

```text
paths.py
  |- unified_extractor.py: PDF, 이미지, 보고서, SigLIP 경로
  |- text_filter.py: PDF, 텍스트 JSON, 모델 캐시
  |- embedding_text_image.py: 모든 전처리 결과와 DB 경로
  |- image_index.py: 이미지 경로와 상대 경로 변환
  |- rag_search.py: 이미지 경로 복구와 단계 문맥표
  `- app_runtime.py: DB와 단계 문맥표
```

## 6. 수정 시 주의사항

1. 파일명만 바꾸고 `paths.py`를 수정하지 않으면 전처리와 앱이 서로 다른 파일을 볼 수 있다.
2. `VECTOR_DB_DIR`를 변경하면 기존 DB를 새 위치에서 찾지 못하므로 다시 구축하거나 폴더를 이동해야 한다.
3. `STAGE_CONTEXT_MAP_MANUAL_PATH`는 앱의 자동·수동 G4 모드가 모두 사용한다.
4. `SCIE_DIR`는 이름이 `SCIE`로 시작하는 첫 번째 폴더를 선택하므로 같은 이름으로 시작하는 폴더가 여러 개면 의도하지 않은 폴더가 선택될 수 있다.

