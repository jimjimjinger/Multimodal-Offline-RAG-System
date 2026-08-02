# `src/app_runtime.py` 상세 설명서

## 1. 파일 역할

`app_runtime.py`는 세 모델 앱이 공유하는 Streamlit 실행 로직이다.

이 파일이 담당하는 작업은 다음과 같다.

1. BGE-M3와 ChromaDB collection 로드
2. G4 단계 profile 로드와 자동 분류
3. G3/G4 멀티모달 검색 호출
4. 검색 텍스트를 Ollama 로컬 LLM prompt로 전달
5. 답변, 검색 원문, 이미지 후보를 화면에 표시

Qwen, Gemma, Llama 앱은 모델 ID만 다르게 지정하고 이 파일의 `run_app()`을 공통으로 호출한다.

## 2. 외부 서비스와 자원

| 자원 | 용도 |
|---|---|
| BGE-M3 | 질문 임베딩과 단계 분류 |
| ChromaDB | 텍스트·이미지 저장소 |
| Ollama `localhost:11434` | 로컬 LLM 응답 생성 |
| Streamlit | 사용자 화면 |
| PIL | 이미지 파일 열기 |

## 3. 함수 설명

### 3.1 `load_resources()`

`@st.cache_resource`가 적용된 함수이다.

#### 처리

1. Hugging Face 캐시 경로를 설정한다.
2. BGE-M3 SentenceTransformer를 불러온다.
3. 영구 ChromaDB client를 연다.
4. `open_rag_collections()`로 텍스트와 이미지 collection을 정확 검색 wrapper로 연다.

#### 반환

`(embedder, text_collection, image_collection)`

Streamlit이 함수를 cache하므로 화면이 다시 실행될 때마다 모델과 DB를 다시 읽지 않는다.

### 3.2 `load_stage_classifier_resources(_embedder)`

`@st.cache_resource`가 적용된다.

#### 처리

1. 수동 검토 단계 map에서 profile을 만든다.
2. BGE-M3로 profile 임베딩을 계산한다.
3. `(stage_profiles, stage_profile_embeddings)`를 반환한다.

매개변수 이름 앞 `_`는 Streamlit이 이 객체 자체를 cache key로 hash하지 않도록 하는 관례이다.

### 3.3 `generate_answer(model_id, question, context)`

#### 목적

검색된 매뉴얼 텍스트를 Ollama 모델에 전달하고 한국어 답변을 받는다.

#### prompt 규칙

모델에 다음을 명시한다.

- 두산로보틱스 협동 로봇 한국어 기술 지원 역할
- 한국어로만 답변
- 제공된 매뉴얼 문맥만 사용
- 근거가 부족하면 부족하다고 답변
- 사실을 만들어내지 않음

검색 문맥과 사용자 질문을 구분된 영역에 넣는다.

#### Ollama 요청

```json
{
  "model": "모델 ID",
  "stream": false,
  "prompt": "...",
  "options": {
    "temperature": 0.2,
    "num_ctx": 4096
  }
}
```

`http://localhost:11434/api/generate`에 최대 180초 timeout으로 POST 요청을 보낸다.

#### 반환과 오류 처리

- 정상 `response` 필드: 답변 문자열
- response 필드 없음: 응답 형식 오류 문자열
- timeout: 모델 생성 지연 안내
- 기타 예외: Ollama 연동 실패 안내

오류를 예외로 다시 발생시키지 않고 사용자 화면에 표시할 문자열로 반환한다.

### 3.4 `render_sidebar(model_id, model_label, image_collection)`

#### 목적

모델과 검색 설정을 보여주고 G4 단계 모드를 선택받는다.

#### 표시 정보

- BGE-M3, ChromaDB, 현재 LLM
- 답변 텍스트 Top-5
- 이미지 후보 검색 수
- 최종 이미지 Top-10
- 이미지 DB 사용 가능 여부

#### 단계 모드

1. `자동 분류`
2. `수동 선택`
3. `G4 사용 안 함`

수동 선택이면 단계 context map의 단계명을 select box에 넣는다. 자동 분류이면 최소 점수와 margin 기준을 설명한다.

#### 반환

```python
{
    "mode": 선택 모드,
    "manual_stage": 수동 단계 또는 None
}
```

### 3.5 `resolve_stage_label(...)`

#### 목적

화면 선택을 검색 함수가 이해할 `stage_label`로 바꾼다.

#### 분기

- G4 사용 안 함: `(None, None)`
- 수동 선택: `(선택 단계, None)`
- 자동 분류: `classify_stage()` 호출 후 `(stage_label, classification)`

자동 분류가 기준에 실패하면 classification 결과는 존재하지만 `stage_label`은 `None`이다.

### 3.6 `render_stage_classification(classification)`

#### 목적

자동 단계 분류 결과와 G4 적용 여부를 화면에 보여준다.

#### 성공

최종 단계, 최고 점수, margin을 `st.info()`로 표시한다.

#### 실패

G4를 적용하지 않았다는 경고와 최고 후보, 점수, margin을 표시한다.

#### 상세 후보

expander 안에 상위 단계 후보와 점수를 순서대로 보여준다.

수동 단계 또는 G4 비활성 모드에서는 classification이 `None`이므로 아무것도 표시하지 않는다.

### 3.7 `render_answer_sources(retrieved_docs, retrieved_metas)`

텍스트 Top-5 원문을 expander 안에 표시한다.

각 결과에 순위, section 제목, 페이지, 본문을 보여준다. 문서와 메타데이터를 `zip()`으로 함께 순회한다.

### 3.8 `render_images(images)`

#### 이미지 없음

도면을 찾지 못했다는 경고를 표시한다.

#### 이미지 있음

각 결과의 경로를 PIL로 열고 다음 caption과 함께 Streamlit 이미지로 표시한다.

- 최종 순위
- 최종 점수
- 파일명
- 연결 제목
- 페이지

현재 이미지 열기 예외를 별도로 처리하지 않으므로 파일이 손상되었거나 사라지면 화면 실행 중 오류가 발생할 수 있다.

### 3.9 `run_app(model_id, model_label, page_title)`

#### 목적

하나의 모델 앱 전체 실행을 구성하는 최상위 함수이다.

#### 1단계: 페이지와 자원

1. wide layout과 브라우저 제목을 설정한다.
2. BGE-M3와 DB collection을 cache에서 가져온다.
3. sidebar를 렌더링한다.

#### 2단계: 질문 입력

앱 제목과 검색 설명을 표시하고 `st.text_input()`으로 질문을 받는다. 질문이 비어 있으면 즉시 반환한다.

Streamlit은 입력이 바뀔 때 스크립트를 위에서 다시 실행하지만 cache된 모델과 DB는 재사용한다.

#### 3단계: 단계 분류

- 자동 모드일 때만 단계 profile과 임베딩을 로드한다.
- `resolve_stage_label()`로 단계 label을 정한다.
- 자동 분류 상세를 표시한다.

#### 4단계: 멀티모달 검색

`retrieve_multimodal()`에 질문, embedder, 두 collection, Top-k 설정, 단계 label, 단계 context map 경로를 전달한다.

텍스트 결과가 없으면 오류를 표시하고 종료한다.

#### 5단계: 로컬 LLM 답변

검색 Top-5를 합친 `retrieval["context"]`를 `generate_answer()`에 전달한다. spinner로 생성 중임을 표시한다.

#### 6단계: 결과 화면

화면을 60:40 두 열로 나눈다.

- 왼쪽: 로컬 LLM 답변과 검색 원문
- 오른쪽: 관련 이미지 Top-10

## 4. G3/G4 모드별 동작

| 화면 모드 | stage label | 검색 동작 |
|---|---|---|
| G4 사용 안 함 | `None` | G3 |
| 수동 선택 | 선택 단계 | G4 |
| 자동 분류 성공 | 추정 단계 | G4 |
| 자동 분류 실패 | `None` | G3 fallback |

## 5. 데이터 흐름

```text
질문 입력
  |- BGE-M3 단계 분류
  |- rag_search.retrieve_multimodal()
  |    |- 텍스트 Top-5
  |    |- 이미지 Top-10
  |    `- LLM용 context
  |- Ollama generate
  `- Streamlit 화면
       |- 답변
       |- 원문
       `- 이미지
```

## 6. 오프라인 동작 범위

다음 조건이 이미 준비되어 있으면 앱 질문 처리 과정에서 외부 API가 필요하지 않다.

- BGE-M3 캐시
- ChromaDB
- 로컬 이미지 파일
- 단계 map
- Ollama와 로컬 LLM 모델

Ollama 요청은 `localhost`로만 전송된다.

## 7. 실행 시 주의사항

1. Ollama 서버가 먼저 실행되어 있어야 한다.
2. 선택한 모델 ID가 Ollama에 설치되어 있어야 한다.
3. ChromaDB가 없거나 텍스트 collection이 없으면 앱 자원 로드가 실패한다.
4. 앱 시작 시 exact wrapper가 전체 임베딩을 RAM에 올린다.
5. 단계 map이나 DB를 수정한 뒤에는 Streamlit resource cache를 초기화하거나 앱을 재시작해야 한다.
6. `generate_answer()`의 `num_ctx=4096`과 텍스트 Top-5 길이에 따라 prompt가 모델 context 한계에 가까워질 수 있다.

