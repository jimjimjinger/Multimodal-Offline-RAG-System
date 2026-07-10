# 논문 초안 v1.1

> 본 문서는 SCIE/IEEE Access 투고용 영문 원고를 작성하기 전의 국문 작업 초안이다.  
> 문장 표현, 참고문헌, 그림/도식 구성은 이후 보완이 필요하다. 검색 성능 결과, 응답 품질 평가, G4 우선 검토 대상 연구자 검토 결과, 오프라인/제한 자원 실행 목표를 반영하였다.

## 제목 후보

**A Context-Aware Multimodal Retrieval-Augmented Generation Framework for Collaborative Robot Training**

대안 제목:

**Improving Multimodal Retrieval for Collaborative Robot Training Using Context-Aware Retrieval-Augmented Generation**

## 초록

협동 로봇 실습 교육에서는 학습자가 매뉴얼의 절차 설명, 설정값, 안전 조건, 이미지 및 도식 자료를 함께 이해해야 한다. 그러나 일반적인 텍스트 기반 검색 또는 텍스트 기반 RAG 시스템은 실습 화면, 배선도, 설정 화면과 같은 시각 자료를 충분히 활용하지 못하며, 학습자의 현재 실습 단계와 관련된 정보를 우선적으로 제공하는 데 한계가 있다. 본 연구에서는 협동 로봇 실습 환경을 위한 상황 인지형 멀티모달 검색 증강 생성 프레임워크를 제안한다. 제안 시스템은 협동 로봇 매뉴얼에서 추출한 텍스트 chunk와 이미지/도식 자료를 각각 인덱싱하고, 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 결합하여 관련 자료를 검색한다. 또한 질문에서 실습 단계를 추정하고, 실습 단계별 page 범위, section heading, 핵심 keyword로 구성된 context map을 이용하여 검색 후보를 재순위화함으로써 정답 이미지의 순위를 개선한다. 시스템은 외부 API 의존도를 줄이고 로컬 벡터 데이터베이스와 4-bit 양자화 LLM을 사용하여 오프라인 환경 및 8GB RAM급 제한 장비에서의 활용 가능성을 목표로 설계하였다.

실험을 위해 협동 로봇 실습 매뉴얼 기반 70개 질의셋을 구성하고, 각 질의에 대해 정답 텍스트, 정답 이미지, 실습 단계 라벨을 부여하였다. 비교군은 키워드 기반 검색(G1), 텍스트 기반 RAG(G2), 멀티모달 RAG(G3), 단계 추정 기반 상황 인지형 멀티모달 RAG(G4)로 구성하였다. 실험 결과, G4는 G3 대비 Image Recall@5를 70.0%에서 75.7%로, Image Recall@10을 75.7%에서 87.1%로, Image MRR을 0.485에서 0.539로 개선하였다. 이는 실습 단계 추정 기반 context-aware re-ranking이 협동 로봇 실습 매뉴얼의 이미지/도식 검색 성능을 개선할 수 있음을 보여준다. 다만 질문 기반 단계 추정 오차와 동일 page 또는 동일 section 내 유사 이미지가 많은 경우에는 여전히 정답 이미지를 세밀하게 구분하는 데 한계가 있었다. 본 연구는 협동 로봇 실습 교육에서 텍스트, 이미지, 실습 단계 정보를 결합한 멀티모달 RAG의 가능성과 한계를 실험적으로 제시한다.

## 키워드

Collaborative robot training, multimodal RAG, retrieval-augmented generation, context-aware retrieval, engineering education, robot manual retrieval

## 1. 서론

협동 로봇은 제조, 교육, 연구 환경에서 인간과 같은 공간에서 작업할 수 있는 로봇으로 활용되고 있다. 특히 공학 교육 현장에서는 협동 로봇 실습을 통해 학습자가 로봇의 설치, 좌표 설정, 안전 설정, 직접 교시, 프로그램 실행 등의 절차를 경험한다. 이러한 실습은 단순한 이론 학습과 달리 매뉴얼의 단계별 설명, 티치 펜던트 화면, 배선도, 안전 설정 이미지 등 다양한 자료를 함께 참고해야 한다.

그러나 협동 로봇 실습 매뉴얼은 분량이 많고, 텍스트 설명과 이미지/도식 자료가 여러 page에 분산되어 있다. 학습자가 특정 실습 상황에서 필요한 정보를 직접 찾으려면 메뉴명, 설정 항목, 화면 위치, 관련 이미지까지 함께 확인해야 하므로 시간이 오래 걸린다. 또한 초보 학습자는 현재 자신이 수행 중인 실습 단계와 매뉴얼의 어느 부분이 연결되는지 파악하기 어렵다.

최근 검색 증강 생성(Retrieval-Augmented Generation, RAG)은 외부 문서 검색 결과를 언어 모델의 응답 생성에 활용함으로써 도메인 지식 기반 질의응답 성능을 높이는 방법으로 사용되고 있다[1]. 하지만 일반적인 텍스트 기반 RAG는 텍스트 chunk 검색에 초점을 두기 때문에, 실습 매뉴얼에서 중요한 역할을 하는 이미지, 도식, 화면 예시를 충분히 활용하지 못한다. 협동 로봇 실습처럼 시각 자료가 절차 이해에 중요한 환경에서는 텍스트 검색만으로는 학습자에게 필요한 정보를 완전하게 제공하기 어렵다.

본 연구는 이러한 한계를 해결하기 위해 협동 로봇 실습 환경을 위한 상황 인지형 멀티모달 RAG 프레임워크를 제안한다. 제안 시스템은 매뉴얼의 텍스트와 이미지/도식을 함께 검색하고, 실습 단계 정보를 이용하여 관련 자료의 순위를 재조정한다. 이를 통해 단순히 텍스트 답변을 생성하는 것을 넘어, 학습자의 실습 상황과 관련된 텍스트 근거와 이미지 자료를 함께 제공하는 것을 목표로 한다.

본 연구의 주요 기여는 다음과 같다.

1. 협동 로봇 실습 매뉴얼을 대상으로 텍스트, 이미지/도식, 실습 단계 라벨을 포함한 70개 평가 질의셋을 구축하였다.
2. 키워드 검색, 텍스트 기반 RAG, 멀티모달 RAG, 상황 인지형 멀티모달 RAG를 동일 질의셋에서 비교할 수 있는 실험 구조를 설계하였다.
3. 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수를 결합한 멀티모달 검색 구조를 구현하였다.
4. 질문 기반 실습 단계 추정과 단계별 context map을 이용한 re-ranking을 통해 이미지 검색 성능을 개선하였다.
5. 개선 사례와 실패 사례를 분석하여 상황 인지형 멀티모달 RAG의 효과와 한계를 제시하였다.

## 2. 관련 연구

### 2.1 Retrieval-Augmented Generation

RAG는 대규모 언어 모델이 내부 파라미터에 저장된 지식만으로 응답하는 한계를 보완하기 위해 외부 문서 검색 결과를 함께 활용하는 방법이다[1]. 일반적으로 RAG 시스템은 문서를 chunk 단위로 분할하고, 각 chunk를 임베딩한 뒤 벡터 데이터베이스에 저장한다. 사용자의 질문이 입력되면 질문 임베딩과 문서 임베딩 간 유사도를 계산하여 관련 문서를 검색하고, 검색된 문서를 언어 모델의 context로 제공하여 답변을 생성한다.

RAG의 검색 단계는 sparse retrieval과 dense retrieval로 나누어 볼 수 있다. BM25는 키워드 기반 sparse retrieval의 대표적인 기준선으로 사용되며[3], Dense Passage Retrieval(DPR)은 질문과 문서를 dense representation으로 표현하여 검색하는 방법을 제시하였다[2]. 본 연구의 G1은 키워드 기반 기준선에 해당하며, G2는 BGE-M3 임베딩을 이용한 dense retrieval 기반 RAG에 해당한다[4].

기술 매뉴얼, 사내 문서, 교육 자료와 같이 도메인 지식이 명확한 문서에서는 RAG가 유용할 수 있다. 그러나 텍스트 기반 RAG는 주로 문장 또는 문단 단위의 텍스트 검색에 의존하므로, 이미지, 도식, 표, 화면 캡처와 같은 시각 자료가 중요한 문서에서는 한계가 있다. 협동 로봇 실습 매뉴얼도 이러한 유형에 해당한다.

### 2.2 Multimodal Retrieval

멀티모달 검색은 텍스트, 이미지, 도식, 오디오 등 서로 다른 modality의 정보를 함께 활용하여 관련 자료를 찾는 방법이다. 이미지와 텍스트를 같은 임베딩 공간에 매핑하는 비전-언어 모델을 사용하면, 텍스트 질의에 대해 관련 이미지를 검색하거나 이미지와 관련된 텍스트를 연결할 수 있다. CLIP은 자연어 supervision을 이용하여 이미지와 텍스트를 연결하는 대표적인 비전-언어 모델이며[5], SigLIP은 sigmoid loss를 사용하여 image-text pre-training을 수행하는 방식으로 제안되었다[6].

실습 매뉴얼에서는 하나의 절차가 텍스트 설명과 이미지 자료로 함께 구성되는 경우가 많다. 예를 들어 특정 메뉴 경로는 텍스트로 설명되지만, 실제 학습자는 티치 펜던트 화면 이미지나 설정 화면을 함께 확인해야 한다. 따라서 텍스트 검색 결과와 이미지 검색 결과를 독립적으로 제공하는 것만으로는 부족하며, 텍스트와 이미지가 어떤 page와 실습 단계에서 연결되는지 함께 고려해야 한다.

### 2.3 Context-Aware Retrieval for Training Guidance

실습 교육 환경에서 학습자의 질문은 독립적인 정보 검색 요청이 아니라 특정 실습 단계와 연결된다. 같은 단어가 포함된 질문이라도 설치 단계, 안전 설정 단계, 프로그램 실행 단계에 따라 필요한 답변과 관련 이미지가 달라질 수 있다. 협동 로봇 교육 관련 연구에서도 이론 설명뿐 아니라 hands-on laboratory exercise, 안전, 조작, 프로그래밍 등 실습 모듈의 중요성이 강조되어 왔다[12]. 따라서 실습 안내 시스템은 질문의 표면적 유사도뿐 아니라 현재 실습 단계와 매뉴얼 구조를 함께 고려해야 한다.

본 연구에서는 이러한 문제를 해결하기 위해 질문에서 실습 단계를 추정하고, 실습 단계별 page 범위, section heading, 핵심 keyword로 구성된 context map을 멀티모달 검색 결과의 re-ranking에 활용한다.

## 3. 제안 프레임워크

### 3.1 전체 구조

제안 시스템은 협동 로봇 실습 매뉴얼을 기반으로 텍스트와 이미지/도식 자료를 전처리하고, 이를 검색 가능한 형태로 인덱싱한다. 사용자가 실습 관련 질문을 입력하면 시스템은 관련 텍스트 chunk와 이미지 후보를 검색한 뒤, 선택된 로컬 LLM을 이용하여 답변을 생성한다.

전체 파이프라인은 다음과 같다.

1. 매뉴얼 PDF에서 텍스트와 이미지/도식 자료를 추출한다.
2. 텍스트를 chunk 단위로 분할하고 page, section, 주변 문맥 정보를 함께 저장한다.
3. 이미지 파일에 page 정보와 주변 텍스트 정보를 연결한다.
4. 텍스트 임베딩과 이미지 관련 임베딩을 생성하여 벡터 데이터베이스에 저장한다.
5. 사용자의 질문에 대해 텍스트 후보와 이미지 후보를 검색한다.
6. G3에서는 텍스트 검색, 이미지 검색, page proximity, 텍스트-이미지 매핑 점수를 결합한다.
7. G4에서는 질문에서 실습 단계를 추정하고, 해당 단계의 context map을 반영하여 후보 순위를 재조정한다.
8. 검색된 근거를 바탕으로 로컬 LLM이 실습 안내 답변을 생성한다.

### 3.2 텍스트 전처리와 인덱싱

매뉴얼에서 추출한 텍스트는 실습 절차와 의미 단위가 유지되도록 chunk로 분할하였다. 각 chunk에는 원문 텍스트, page 번호, section 관련 정보가 함께 저장된다. 텍스트 검색에는 BGE-M3 기반 임베딩을 사용하며, 벡터 데이터베이스는 ChromaDB를 사용한다.

텍스트 기반 RAG인 G2에서는 질문 임베딩과 텍스트 chunk 임베딩 간 유사도를 기반으로 Top-k 텍스트 후보를 검색한다. 검색된 텍스트 후보는 LLM 답변 생성의 근거로 사용된다.

### 3.3 이미지/도식 전처리와 검색

매뉴얼에서 추출한 이미지/도식 자료는 파일명과 page 정보를 기준으로 관리된다. 이미지 자료는 단독으로 의미를 갖기 어려운 경우가 많으므로, 주변 텍스트와 page 정보를 함께 활용한다. 또한 이미지 후보 검색에서는 이미지 전용 검색 결과와 텍스트 검색 결과의 page proximity를 함께 고려한다.

G3에서는 이미지 검색 성능을 높이기 위해 다음 점수를 결합한다.

- 이미지 전용 검색 점수
- 텍스트 검색 결과와 이미지 page 간 근접도
- 텍스트-이미지 매핑 점수
- 기본 후보 순위 점수

이를 통해 사용자의 질문과 직접적으로 관련된 텍스트 근거뿐 아니라, 해당 텍스트와 가까운 page에 위치한 이미지/도식 자료를 함께 검색한다.

### 3.4 상황 인지형 re-ranking

G4는 G3 구조에 실습 단계 추정과 context map 기반 re-ranking을 추가한 방식이다. context map은 각 실습 단계에 대해 관련 page 범위, section heading, 핵심 keyword, 매핑 근거를 포함한다. 이 매핑표는 정답 이미지 파일명이나 정답 chunk ID를 사용하지 않고, 매뉴얼의 section 구조와 실습 단계 의미를 기준으로 수동 검토하여 구성하였다.

G4의 re-ranking은 다음 방식으로 이루어진다.

1. 질문과 실습 단계 context profile 간 BGE-M3 의미 유사도를 비교하여 실습 단계를 추정한다.
2. 분류 신뢰도가 낮거나 1위와 2위 후보가 애매하면 G4를 강제 적용하지 않고 G3 방식으로 fallback한다.
3. 추정된 실습 단계와 연결된 page 범위와 keyword를 불러온다.
4. 검색 후보가 관련 page 범위에 포함되면 추가 점수를 부여한다.
5. 후보의 주변 텍스트 또는 section 정보가 keyword와 일치하면 점수를 보정한다.
6. 기존 G3 점수와 context 점수를 결합하여 최종 순위를 계산한다.

이 방식은 검색 후보를 정답 라벨로 직접 선택하는 것이 아니라, 매뉴얼 구조와 실습 단계 정보를 이용하여 후보의 우선순위를 조정한다는 점에서 상황 인지형 검색 구조로 해석할 수 있다.

### 3.5 로컬 LLM 기반 응답 생성과 제한 자원 설계

본 시스템은 제한된 환경에서의 활용 가능성을 고려하여 로컬 LLM 기반 응답 생성을 목표로 한다. 실험 및 앱 구동에서는 Qwen, Gemma, Llama 계열의 로컬 모델을 비교할 수 있도록 구성하였다. 응답 생성 단계에서는 검색된 텍스트 근거와 이미지 후보 정보를 context로 제공하고, 사용자의 질문에 대한 실습 안내 답변을 생성한다.

오프라인 구동을 위해 앱 실행 단계는 외부 LLM API를 호출하지 않고 Ollama 기반 로컬 모델을 사용한다. 모델은 7B~9B급 Q4 양자화 모델을 중심으로 구성하여 저장 용량과 메모리 사용량을 줄였다. 또한 SigLIP 기반 텍스트-이미지 유사도 계산과 같은 무거운 멀티모달 처리는 전처리 단계에서 수행하고, 앱 실행 단계에서는 저장된 인덱스와 매핑 정보를 활용하도록 설계하였다. 따라서 본 시스템의 설계 목표는 고성능 클라우드 모델이 없는 환경에서도 협동 로봇 실습 질의에 대해 텍스트 근거와 관련 이미지를 함께 제공하는 것이다.

다만 본 초안의 정량 결과는 우선 검색 성능 중심으로 정리하였다. 응답 품질 평가는 별도 기준에 따라 rubric 기반 1차 평가를 수행하고, G4 오류 및 애매 사례 중심의 우선 검토 대상에 대해 연구자 수동 검토를 보완하였다.

## 4. 실험 설계

### 4.1 데이터셋

실험 데이터는 협동 로봇 실습 매뉴얼에서 구성하였다. 총 70개의 질의를 만들었고, 각 질의에는 정답 텍스트, 정답 이미지, 실습 단계 라벨을 부여하였다. 질의는 설치, 전원, 티치 펜던트 조작, 직접 교시, 좌표 설정, 안전 설정, I/O 배선, 시스템 관리 등 협동 로봇 실습에서 자주 등장하는 절차를 포함한다.

질의셋은 정답 이미지가 명확히 특정될 수 있는 질문을 중심으로 구성하였다. 이는 멀티모달 RAG의 이미지 검색 성능을 정량적으로 평가하기 위한 것이다.

### 4.2 비교군

실험 비교군은 다음 네 가지로 구성하였다.

| 비교군 | 이름 | 설명 |
|---|---|---|
| G1 | Keyword Search | 질문과 텍스트 chunk의 키워드 일치도를 기반으로 검색 |
| G2 | Text-only RAG | BGE-M3 텍스트 임베딩 기반 텍스트 chunk 검색 |
| G3 | Multimodal RAG | 텍스트 검색, 이미지 검색, page proximity, 텍스트-이미지 매핑 점수 결합 |
| G4 | Context-aware Multimodal RAG | 질문에서 실습 단계를 추정하고 G3 후보에 context map 기반 re-ranking 추가 |

G1과 G2는 텍스트 검색 성능을 비교하기 위한 baseline이다. G3는 이미지/도식 정보를 추가한 멀티모달 검색 구조이며, G4는 실습 단계 정보를 반영하여 멀티모달 검색 후보를 재순위화하는 제안 방식이다.

### 4.3 평가 지표

검색 성능은 Recall@k와 MRR을 사용하여 평가하였다.

Text Recall@k는 Top-k 텍스트 후보 안에 정답 텍스트가 포함되는 비율이다. Image Recall@k는 Top-k 이미지 후보 안에 정답 이미지가 포함되는 비율이다. MRR은 정답 후보가 검색 결과에서 얼마나 높은 순위에 위치하는지를 평가한다. 또한 멀티모달 검색의 관점에서 Top-k 안에 정답 텍스트와 정답 이미지가 모두 포함되는지를 Both@k로 평가하였다.

텍스트 검색 평가는 파일럿 단계에서 relaxed 기준을 사용하였다. 정답 문장과 완전히 동일하지 않더라도 같은 page, 핵심 keyword 포함, 의미 유사성이 충분한 경우 정답으로 인정하였다. 이미지 검색은 정답 이미지 파일명이 Top-k 후보 안에 포함되는지를 기준으로 평가하였다.

### 4.4 실험 환경

실험은 로컬 노트북 환경에서 수행하였다. 본 연구는 제한된 환경에서 구동 가능한 오프라인 RAG 시스템을 지향하지만, 현재 정량 실험은 개발 및 평가용 노트북에서 수행한 결과이다. 따라서 본 논문에서의 8GB RAM급 환경은 시스템 설계 목표와 모델 선택 기준으로 제시하고, 실제 8GB 이하 장비에서의 속도, 메모리 사용량, 동시 실행 안정성 측정은 후속 재현성 검증 항목으로 남겨둔다.

| 항목 | 내용 |
|---|---|
| 운영체제 | Windows |
| 장비 | HP OMEN Gaming Laptop 16-am0xxx |
| CPU | Intel Core Ultra 7 255H, 16 cores / 16 logical processors |
| RAM | 약 24GB |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU, Intel Graphics |
| Python | 3.12.10 (`.venv`) |
| Vector DB | ChromaDB 1.5.9 |
| App framework | Streamlit 1.58.0 |
| Embedding / ML stack | sentence-transformers 5.6.0, transformers 5.12.1, torch 2.12.1 |
| Data processing | pandas 3.0.3, PyMuPDF 1.27.2.3, Pillow 12.2.0 |

로컬 LLM은 Ollama 기반으로 실행하도록 구성하였다. 현재 프로젝트에는 다음 모델이 포함되어 있다.

| 모델 | 로컬 모델 ID | 앱 파일 | 로컬 저장 크기 |
|---|---|---|---:|
| Qwen 2.5 7B Q4 | `qwen2.5:7b` | `src/app_qwen.py` | 약 4.36GB |
| Gemma 2 9B Q4 | `gemma2:9b` | `src/app_gemma.py` | 약 5.07GB |
| Llama 3.1 8B Q4 | `llama3.1:8b` | `src/app_llama.py` | 약 4.58GB |

추가로 `qwen2.5:1.5b`, `gemma2:2b`, `exaone3.5:7.8b` 모델도 로컬 저장소에 존재하지만, 현재 비교 앱의 기본 대상은 Qwen 2.5 7B, Gemma 2 9B, Llama 3.1 8B이다.

## 5. 실험 결과

### 5.1 전체 검색 성능

다음 표는 G1, G2, G3, G4의 최종 검색 성능을 나타낸다.

| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 Keyword Search | 75.7% | 95.7% | 98.6% | 0.837 | - | - | - | - | - | - |
| G2 Text-only RAG | 81.4% | 95.7% | 100.0% | 0.879 | - | - | - | - | - | - |
| G3 Multimodal RAG | 81.4% | 95.7% | 100.0% | 0.879 | 32.9% | 70.0% | 75.7% | 0.485 | 70.0% | 75.7% |
| G4 Context-aware Multimodal RAG | 85.7% | 95.7% | 100.0% | 0.903 | 37.1% | 75.7% | 87.1% | 0.539 | 75.7% | 87.1% |

G1은 단순 키워드 검색임에도 Text Recall@5가 95.7%로 높게 나타났다. 이는 협동 로봇 매뉴얼 질의가 메뉴명, 설정값, 기능명 등 명시적인 기술 용어를 포함하기 때문으로 볼 수 있다. 그러나 Text Recall@1과 Text MRR에서는 G2가 G1보다 높은 성능을 보였다. 이는 임베딩 기반 텍스트 검색이 키워드 기반 검색보다 정답 텍스트를 더 상위에 배치하는 데 효과가 있음을 의미한다.

G2와 G3는 동일한 텍스트 검색 경로를 사용하므로 텍스트 성능은 동일하게 나타났다. G3의 의의는 이미지/도식 검색을 추가했다는 점에 있다. G3는 Image Recall@5 70.0%, Image Recall@10 75.7%를 보였으나, Image Recall@1은 32.9%, Image MRR은 0.485로 낮았다. 이는 정답 이미지가 후보군 안에 포함되는 경우는 많지만, 상위 순위에 안정적으로 배치되지는 못했음을 보여준다.

G4는 G3 대비 이미지 검색 성능을 개선하였다. Image Recall@5는 70.0%에서 75.7%로, Image Recall@10은 75.7%에서 87.1%로 상승하였다. Image MRR도 0.485에서 0.539로 증가하였다. 또한 Both@5는 70.0%에서 75.7%로, Both@10은 75.7%에서 87.1%로 개선되었다. 이는 질문 기반 실습 단계 추정과 context map 기반 re-ranking이 텍스트와 이미지가 함께 필요한 실습 질의에서 효과적으로 작동했음을 시사한다.

### 5.2 G4 개선 사례

G4의 효과는 개별 사례에서도 확인된다.

첫째, Q31은 티치 펜던트에 위치한 USB 포트의 주된 용도를 묻는 질문이다. G3에서는 정답 이미지 `page_103_img_0_0.jpeg`가 Top-10 밖에 있었으나, G4에서는 3위로 상승하였다. 이는 질문이 `티치 펜던트/USB 데이터 관리` 단계로 추정되었고, USB port, pendant, data import/export 관련 context가 반영되었기 때문이다.

둘째, Q23은 로봇 시스템의 시간 기능을 확인하는 화면 영역을 묻는 질문이다. G3에서는 정답 이미지 `page_167_img_3_0.jpeg`가 Top-10 밖에 있었으나, G4에서는 5위로 상승하였다. 이는 질문이 `UI/시스템 정보 확인` 단계로 추정되었고, system information, time, screen area 관련 context가 이미지 후보 재순위화에 반영되었기 때문이다.

셋째, Q02는 제어기의 전원 공급을 위해 필요한 접지 조건을 묻는 질문이다. G3에서는 정답 이미지 `page_403_img_0_0.jpeg`가 Top-10 밖에 있었으나, G4에서는 5위로 상승하였다. 이는 질문이 `안전/전원/접지` 단계로 추정되었고, grounding, power supply, controller, safety 관련 context가 반영되어 정답 이미지가 Top-5 안으로 이동한 사례이다.

이러한 사례는 G4가 단순히 전체 Recall을 높인 것이 아니라, 실제 실습 단계 정보를 이용하여 정답 이미지의 순위를 개선했음을 보여준다.

### 5.3 G4 실패 사례

G4는 전체적으로 G3보다 개선되었지만, 일부 질의에서는 여전히 한계를 보였다.

Q10은 티치 펜던트 화면에서 로봇의 현재 각 관절 각도를 확인하는 메뉴 경로를 묻는 질문이다. G4는 Status 관련 page와 keyword를 반영했지만, 정답 이미지 `page_332_img_0_0.jpeg`를 Top-10 안에 포함하지 못했다. 이는 `Status`, `I/O Overview`, `joint angle`과 같은 keyword가 후보 수집 단계에서 충분히 강하게 작동하지 못했기 때문으로 해석된다.

Q28은 로봇 cube module cable의 방수 등급 강화를 위한 cable 결합 부품을 묻는 질문이다. G4는 page 405 주변의 관련 이미지를 여러 개 상위 후보로 올렸지만, 정확한 정답 이미지 `page_405_img_0_0.jpeg`는 Top-10 안에 포함하지 못했다. 이는 같은 page 내 여러 이미지 중 정확한 세부 이미지를 구분하는 image-level distinction이 부족함을 보여준다.

Q15는 시스템의 과거 오류 로그를 추출하는 메뉴 경로를 묻는 질문이다. 이 경우 질문 기반 단계 추정이 `시스템 관리/로그`가 아니라 `UI/시스템 정보 확인`으로 치우쳤고, 정답 이미지 `page_340_img_0_0.jpeg`는 Top-10 안에 포함되지 못했다. 이는 G4의 성능이 단계 추정 정확도에 영향을 받는다는 점을 보여준다.

이러한 실패 사례는 향후 이미지 caption, bbox 주변 텍스트, 이미지 순서, 세부 단계 라벨을 추가로 활용해야 함을 시사한다.

## 6. 응답 품질 평가 결과

검색 성능은 RAG 시스템의 기반 성능을 보여주지만, 실제 실습 보조 도구로서의 유용성을 평가하기 위해서는 생성 응답의 품질도 함께 확인해야 한다. 본 연구에서는 G2, G3, G4 조건에서 Qwen, Gemma, Llama 모델의 응답을 생성하고, 70개 질의에 대해 총 630개 응답을 평가하였다.

응답 품질 평가는 다음 다섯 가지 기준으로 수행한다.

1. 정확성: 정답 텍스트의 핵심 내용과 일치하는가?
2. 구체성: 메뉴 경로, 버튼명, 설정값, 절차가 충분히 구체적인가?
3. 실습 단계 적합성: 질문의 실습 단계와 맞는 안내를 제공하는가?
4. 안전성: 위험하거나 잘못된 로봇 조작을 안내하지 않는가?
5. 이해 용이성: 초보 학습자가 이해하기 쉬운 표현으로 설명하는가?

각 항목은 1점에서 5점까지 평가하고, 평균 점수를 기준으로 모델 및 비교군별 응답 품질을 분석하였다. 전체 630개 응답에 대해서는 rubric 기반 1차 평가를 수행하였다. 추가로 1차 평가 결과 중 G4 응답의 오류 및 애매 사례, 그리고 G4 개선/실패 대표 사례를 포함한 54개 우선 검토 대상에 대해 연구자 수동 검토를 수행하였다.

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

연구자 수동 검토는 전체 630개 응답을 모두 재채점한 것이 아니라, G4 결과 중 논문 해석에 영향을 줄 수 있는 54개 우선 검토 대상을 확인하는 방식으로 수행하였다. 검토 대상은 G4 응답 중 X 판정 전체, G4-Qwen 응답 중 △ 판정, G4 개선 사례 3개, G4 실패 사례 3개로 구성하였다.

| 연구자 검토 대상 | 검토 수 | O | △ | X |
|---|---:|---:|---:|---:|
| G4 우선 검토 대상 | 54 | 13 | 6 | 35 |

이 연구자 검토 결과는 전체 응답 품질의 평균 성능을 대체하는 지표가 아니라, G4 결과 중 논문 해석에 민감한 오류 및 애매 사례를 확인하기 위한 보완 지표이다. 따라서 논문에서는 응답 품질 결과를 검색 성능 개선의 직접 증거로 과도하게 사용하지 않고, 로컬 LLM 기반 실습 안내 응답의 가능성과 한계를 설명하는 보조 결과로 제시한다.

응답 품질 평가에서는 Qwen 기반 응답이 전반적으로 가장 안정적인 결과를 보였다. 다만 검색 성능과 달리 생성 응답 품질에서는 G4가 모든 모델에서 일관된 개선을 보이지는 않았다. Qwen은 G2에서 4.05점, G3에서 4.01점, G4에서 3.99점으로 모두 4점 내외의 안정적인 성능을 보였으나, G4에서 평균 점수는 소폭 낮아졌다. Gemma는 G3 3.56점에서 G4 3.59점으로 거의 유지되었고, Llama도 G3 3.60점에서 G4 3.62점으로 소폭 상승하였다.

이 결과는 검색 성능과 응답 품질이 항상 동일하게 움직이지는 않음을 보여준다. G4는 이미지 검색 성능에서는 뚜렷한 개선을 보였지만, 텍스트 응답 품질에서는 검색 근거의 변화, 질문 기반 단계 추정 결과, 로컬 LLM의 생성 안정성이 함께 작용하였다. 연구자 검토에서도 G4 우선 검토 대상 54개 중 X가 35개로 가장 많았기 때문에, 본 연구의 핵심 기여는 우선 검색 단계의 개선으로 해석하는 것이 타당하다. 응답 품질 개선은 후속 prompt 조정, 근거 구성 방식 개선, 사용자 또는 전문가 평가를 통해 추가 검증할 필요가 있다.

## 7. 논의

실험 결과는 협동 로봇 실습 매뉴얼 기반 RAG에서 텍스트 검색보다 이미지 검색이 더 어려운 문제임을 보여준다. 텍스트 검색은 G1에서도 높은 Recall@5를 보였고, G2와 G3에서는 Text Recall@10이 100.0%에 도달하였다. 반면 이미지 검색은 G3에서 Image Recall@1이 32.9%에 그쳤다. 이는 텍스트 질의와 매뉴얼 이미지 사이의 의미적 연결이 직접적이지 않고, 이미지가 page 및 주변 텍스트에 의존하는 경우가 많기 때문이다.

G4의 context-aware re-ranking은 이러한 문제를 완전히 해결하지는 못했지만, 정답 이미지의 순위를 개선하는 데 효과가 있었다. 특히 실습 단계와 관련된 page 범위 및 keyword가 명확한 경우에는 정답 이미지가 Top-5 또는 Top-1로 상승하였다. 이는 협동 로봇 실습 환경에서 사용자의 질문을 독립적인 질의로만 처리하는 것이 아니라, 실습 단계와 매뉴얼 구조를 함께 고려해야 함을 보여준다.

다만 G4의 한계도 분명하다. 현재 G4는 page-level 및 section-level context에 강하지만, 같은 page 안에 여러 이미지가 존재하거나 같은 section 안에 유사한 설정 화면이 많은 경우에는 정확한 이미지를 선택하지 못한다. 따라서 향후 연구에서는 이미지 단위 caption 생성, bbox 주변 텍스트 연결, 이미지 순서 정보, 세부 실습 단계 분류를 추가하여 image-level retrieval을 강화할 필요가 있다.

응답 품질 평가에서는 Qwen이 세 비교군 전반에서 가장 안정적인 평균 점수를 보였다. G4-Qwen의 평균 점수는 3.99점으로 G2-Qwen 및 G3-Qwen보다 소폭 낮았지만, 여전히 세 모델 중 가장 높은 G4 응답 품질을 보였다. 이는 제한된 로컬 환경에서 7B급 양자화 모델을 사용하더라도, 적절한 검색 근거가 제공될 경우 실습 안내 응답을 생성할 수 있음을 시사한다. 다만 G4의 검색 성능 개선이 생성 응답 품질 향상으로 항상 직접 연결되지는 않았고, G4 오류 및 애매 사례에 대한 연구자 검토에서도 여전히 보완이 필요한 응답이 확인되었다. 따라서 최종 논문에서는 G4의 기여를 응답 생성 품질의 대폭 향상이 아니라, 검색 근거와 이미지 검색 순위 개선으로 중심화하는 것이 적절하다.

## 8. 결론

본 연구는 협동 로봇 실습 환경을 위한 상황 인지형 멀티모달 RAG 프레임워크를 제안하고, 협동 로봇 실습 매뉴얼 기반 70개 질의셋을 이용해 검색 성능을 평가하였다. 실험 결과, 텍스트 기반 RAG는 매뉴얼 텍스트 검색에서 안정적인 성능을 보였으나, 이미지/도식 자료 검색에서는 추가적인 멀티모달 검색 구조가 필요함을 확인하였다.

멀티모달 RAG인 G3는 이미지 검색 기능을 제공했지만, 정답 이미지를 상위 순위로 배치하는 데 한계가 있었다. 이에 비해 G4는 질문 기반 실습 단계 추정과 단계별 context map을 활용하여 이미지 후보를 재순위화함으로써 G3 대비 Image Recall@5, Image Recall@10, Image MRR을 모두 개선하였다. 특히 Image Recall@5는 70.0%에서 75.7%로, Image MRR은 0.485에서 0.539로 향상되었다.

이 결과는 협동 로봇 실습 매뉴얼처럼 텍스트, 이미지, 절차 정보가 함께 사용되는 교육 환경에서 context-aware multimodal RAG가 검색 성능을 개선할 가능성이 있음을 보여준다. 또한 응답 품질 평가에서는 Qwen이 G2, G3, G4 전반에서 가장 안정적인 결과를 보여, 검색 구조와 로컬 LLM 선택이 함께 시스템 성능에 영향을 준다는 점을 확인하였다. G4 우선 검토 대상에 대한 연구자 검토 결과는 생성 응답 품질에는 여전히 오류와 애매 사례가 존재함을 보여주었으므로, 향후 연구에서는 이미지 단위 구분 능력 강화와 함께 prompt, 근거 구성 방식, 실제 학습자 또는 전문가 평가를 추가로 검증할 계획이다.

## 9. 현재 초안의 보완 필요 사항

본 초안은 검색 성능, rubric 기반 1차 응답 품질 평가, G4 우선 검토 대상 연구자 검토 결과를 중심으로 작성되었으며, 최종 논문 원고로 발전시키기 위해 다음 보완이 필요하다.

1. 관련 연구 참고문헌을 IEEE 양식으로 정리해야 한다.
2. 텍스트 평가의 relaxed 기준을 더 명확히 정의해야 한다.
3. strict 평가를 추가할지 여부를 결정해야 한다.
4. G4 단계 추정과 context map 구축 과정의 객관성을 더 자세히 설명해야 한다.
5. 전체 프레임워크, G3/G4 re-ranking 구조, 실험 파이프라인 그림을 추가해야 한다.
6. 8GB RAM급 제한 환경에서의 실행 가능성을 별도 측정하거나, 현재 단계에서는 설계 목표로만 명확히 제한해 서술해야 한다.
7. 영문 SCIE 원고 형식에 맞게 문체를 변환해야 한다.

## 10. 참고문헌 초안

아래 참고문헌은 영문 원고 작성 전 IEEE 양식에 맞게 다시 정리해야 한다. 현재 단계에서는 관련 연구와 방법론의 근거를 잡기 위한 1차 후보 목록이다.

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," NeurIPS, 2020. https://arxiv.org/abs/2005.11401

[2] V. Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering," EMNLP, 2020. https://aclanthology.org/2020.emnlp-main.550/

[3] S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," Foundations and Trends in Information Retrieval, 2009. https://doi.org/10.1561/1500000019

[4] J. Chen et al., "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation," ACL Findings, 2024. https://arxiv.org/abs/2402.03216

[5] A. Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," ICML, 2021. https://arxiv.org/abs/2103.00020

[6] X. Zhai et al., "Sigmoid Loss for Language Image Pre-Training," arXiv, 2023. https://arxiv.org/abs/2303.15343

[7] Qwen Team, "Qwen2.5 Technical Report," arXiv, 2024. https://arxiv.org/abs/2412.15115

[8] Gemma Team, "Gemma 2: Improving Open Language Models at a Practical Size," arXiv, 2024. https://arxiv.org/abs/2408.00118

[9] Meta AI, "The Llama 3 Herd of Models," arXiv, 2024. https://arxiv.org/abs/2407.21783

[10] T. Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs," NeurIPS, 2023. https://arxiv.org/abs/2305.14314

[11] Chroma, "Chroma Docs: Introduction." https://docs.trychroma.com/docs/overview/introduction

[12] A. Djuric, J. L. Rickli, V. M. Jovanovic, and D. Foster, "Hands-On Learning Environment and Educational Curriculum on Collaborative Robotics," ASEE Annual Conference, 2017. https://digitalcommons.odu.edu/engtech_fac_pubs/78/

[13] Doosan Robotics, "User Manual / DART-Platform Manual." https://manual.doosanrobotics.com/en/user-manual/3.6.0/1-m-h-series/part-6-dart-platform-manual

## 11. 논문에 사용할 핵심 파일

| 용도 | 파일 |
|---|---|
| 최종 정리본 | `SCIE용/18_paper_ready_summary.md` |
| 70개 질의셋 | `SCIE용/excel/03_question_set_70.xlsx` |
| 비교군 정의 | `SCIE용/05_experiment_groups.md` |
| 평가 지표 | `SCIE용/06_metrics.md` |
| G4 context map | `SCIE용/excel/11_stage_context_map_manual.xlsx` |
| G4 최종 결과 | `SCIE용/30_g4_auto_results.md` |
| G4 단계 추정 결과 | `SCIE용/29_stage_classifier_results.md`, `SCIE용/excel/29_stage_classifier_eval.xlsx` |
| G4 oracle-stage 참고 결과 | `SCIE용/12_g4_manual_results.md` |
| G1/G2/G3/G4 비교 결과 | `SCIE용/15_g1_g2_g3_g4_results.md` |
| G4 사례 분석 | `SCIE용/16_g4_case_analysis.md` |
| 응답 품질 평가 기준 | `SCIE용/17_response_quality_eval_criteria.md` |
| 응답 품질 평가 템플릿 | `SCIE용/excel/17_response_quality_eval_template.xlsx` |
| 응답 품질 평가 결과 | `SCIE용/22_response_quality_eval_results.md`, `SCIE용/excel/22_response_quality_eval_results.xlsx` |
| 연구자 검토 체크리스트 | `SCIE용/31_researcher_review_checklist.md`, `SCIE용/excel/31_researcher_review_checklist.xlsx` |
| 논문 표/그림 캡션 | `SCIE용/32_tables_figures_captions.md` |
| G4 context map 구축 절차 | `SCIE용/33_context_map_protocol.md` |
| IEEE Access 준비 체크리스트 | `SCIE용/34_ieee_access_readiness_checklist.md` |
| 텍스트 평가 기준 정책 | `SCIE용/35_text_evaluation_policy.md` |
| 시스템 전체 설명서 | `SCIE용/36_system_full_explanation.md` |
