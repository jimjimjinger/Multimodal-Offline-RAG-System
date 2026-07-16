# 논문 표/그림 캡션 초안

## 목적

이 문서는 IEEE Access 영문 원고로 옮길 때 사용할 표와 그림의 번호, 제목, 캡션 초안을 정리한다. `28_figures_plan.md`가 제작 계획이라면, 본 문서는 실제 원고에 넣을 수 있는 caption 중심 문서이다.

## Figure 목록

### Fig. 1. Overall Architecture of the Proposed Context-Aware Multimodal RAG Framework

**국문 설명:** 제안 시스템의 전체 구조를 보여준다. 협동 로봇 매뉴얼 PDF에서 텍스트와 이미지/도식을 추출하고, BGE-M3와 SigLIP 기반 신호를 이용해 ChromaDB에 인덱싱한 뒤, G1-G4 검색 모듈과 로컬 LLM을 통해 답변과 이미지 근거를 제공하는 흐름을 나타낸다.

**영문 캡션 초안:**  
Overall architecture of the proposed context-aware multimodal retrieval-augmented generation framework for collaborative robot training. The framework consists of offline manual preprocessing, text and image indexing, multimodal retrieval, context-aware re-ranking, and local LLM-based response generation.

**본문 위치:** Section III-A, Proposed Framework

### Fig. 2. Manual Preprocessing and Indexing Pipeline

**국문 설명:** PDF 매뉴얼에서 텍스트 chunk와 이미지/도식 자료가 어떻게 추출되고, page metadata, 주변 텍스트, 텍스트-이미지 매핑 점수와 함께 저장되는지 설명한다.

**영문 캡션 초안:**  
Manual preprocessing and indexing pipeline. Text chunks and visual materials are extracted from the collaborative robot manual, linked with page-level metadata and neighboring textual context, and stored in vector collections for text and image retrieval.

**본문 위치:** Section III-B, Text and Image Preprocessing

### Fig. 3. Multimodal Retrieval Strategy in G3

**국문 설명:** G3 멀티모달 RAG에서 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수가 이미지 후보 순위 산정에 어떻게 결합되는지 보여준다.

**영문 캡션 초안:**  
Multimodal retrieval strategy used in G3. Candidate images are ranked by combining image retrieval scores, text retrieval relevance, page proximity, and text-image mapping signals.

**본문 위치:** Section III-C, Multimodal Retrieval

### Fig. 4. Context-Aware Re-Ranking Strategy in G4

**국문 설명:** G4에서 질문으로부터 실습 단계를 추정하고, 단계별 page range, section heading, keyword로 구성된 context map을 이용해 G3 후보를 재순위화하는 과정을 보여준다.

**영문 캡션 초안:**  
Context-aware re-ranking strategy used in G4. The user query is first matched to a stage context profile, and the retrieved text and image candidates are re-ranked using stage-specific page ranges, section headings, and keywords.

**본문 위치:** Section III-D, Context-Aware Re-Ranking

### Fig. 5. Retrieval Performance Comparison among G1-G4

**국문 설명:** G1, G2, G3, G4의 Text Recall@k, Image Recall@k, MRR, Both@k를 비교한다. G4가 G3 대비 Image Recall@5, Image Recall@10, Image MRR을 개선했지만 Image Recall@1은 여전히 낮다는 점을 함께 보여준다.

**영문 캡션 초안:**  
Retrieval performance comparison among G1, G2, G3, and G4 on the 70-query evaluation set. G4 improves image retrieval performance over G3 while maintaining stable text retrieval performance.

**본문 위치:** Section V-A, Retrieval Performance

### Fig. 6. Representative Successful Cases of G4 Re-Ranking

**국문 설명:** G4가 G3에서 Top-10 밖이던 정답 이미지를 Top-5 안으로 끌어올린 대표 사례를 보여준다. Q31, Q23, Q02를 후보로 사용한다.

**영문 캡션 초안:**  
Representative successful cases of G4 re-ranking. In these cases, the correct image was not retrieved within the top-10 by G3, but was promoted into the top-5 by the context-aware re-ranking in G4.

**본문 위치:** Section V-B, Case Analysis

### Fig. 7. Representative Failure Cases of G4

**국문 설명:** G4에서도 정답 이미지를 찾지 못한 사례를 보여준다. 질문 기반 단계 추정 실패, 같은 page 내 유사 이미지 구분 실패, 세부 화면 단서 부족을 설명한다.

**영문 캡션 초안:**  
Representative failure cases of G4. The errors are mainly caused by insufficient image-level discrimination, ambiguous stage classification, or weak visual cues within the same manual page or section.

**본문 위치:** Section VI, Discussion and Limitations

## Table 목록

### Table I. Composition of the Evaluation Query Set

**내용:** 70개 질의셋의 구성, 질문 유형, 실습 단계, 정답 텍스트/이미지 라벨링 기준.

**관련 파일:** `SCIE용/excel/03_question_set_70.xlsx`

**영문 캡션 초안:**  
Composition of the 70-query evaluation set constructed from the collaborative robot training manual.

### Table II. Experimental Groups

**내용:** G1, G2, G3, G4의 차이와 각 비교군에 포함된 retrieval component.

**관련 파일:** `SCIE용/26_experiment_pipeline.md`

**영문 캡션 초안:**  
Definition of experimental groups used to compare keyword search, text-only RAG, multimodal RAG, and context-aware multimodal RAG.

### Table III. Experimental Environment and Local LLM Configuration

**내용:** OS, CPU, RAM, GPU, Python, ChromaDB, Streamlit, BGE-M3, Ollama 모델 ID 및 모델 크기.

**관련 파일:** `SCIE용/19_paper_draft.md`

**영문 캡션 초안:**  
Experimental environment and local LLM configuration used for retrieval and response generation experiments.

### Table IV. Retrieval Performance of G1-G4

**내용:** Text Recall@1/5/10, Text MRR, Image Recall@1/5/10, Image MRR, Both@5, Both@10.

**관련 파일:** `SCIE용/excel/15_g1_g2_g3_g4_summary.xlsx`

**영문 캡션 초안:**  
Retrieval performance of G1-G4 on the 70-query evaluation set.

### Table V. Stage Classification Performance for G4

**내용:** Top-1/Top-3/Top-5 stage accuracy, G4 적용률, 적용 시 Top-1 accuracy.

**관련 파일:** `SCIE용/29_stage_classifier_results.md`

**영문 캡션 초안:**  
Stage classification performance used for automatic context selection in G4.

### Table VI. Response Quality Evaluation Results

**내용:** G2/G3/G4와 Qwen/Gemma/Llama별 평균 응답 품질 점수, O/△/X 개수.

**관련 파일:** `SCIE용/excel/22_response_quality_eval_summary.xlsx`

**영문 캡션 초안:**  
Rubric-based preliminary response quality evaluation results for local LLMs under G2, G3, and G4 settings.

### Table VII. Representative Improvement and Failure Cases of G4

**내용:** G4 개선 사례 3개와 실패 사례 3개, G3/G4 이미지 순위, 원인 해석.

**관련 파일:** `SCIE용/16_g4_case_analysis.md`

**영문 캡션 초안:**  
Representative improvement and failure cases of G4 compared with G3.

## 우선 제작할 그림

교수님 보고 또는 영문 원고 초안에는 다음 4개를 우선 제작하면 된다.

1. Fig. 1 Overall Architecture
2. Fig. 4 Context-Aware Re-Ranking Strategy
3. Fig. 5 Retrieval Performance Comparison
4. Fig. 6 Representative Successful Cases

Fig. 2, Fig. 3, Fig. 7은 원고 분량과 심사 의견에 따라 추가한다.
