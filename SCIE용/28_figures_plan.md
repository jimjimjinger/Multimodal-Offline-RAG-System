# 논문 그림/도식 계획

## 목적

본 문서는 SCIE/IEEE Access 논문에 넣을 그림과 표의 후보를 정리한다. 실제 그림 제작 전 어떤 내용을 시각화할지 확정하기 위한 계획 문서이다.

## Figure 1. 전체 시스템 아키텍처

### 목적

제안 시스템이 단순 챗봇이 아니라 전처리, 인덱싱, 검색, re-ranking, 응답 생성을 포함한 framework임을 보여준다.

### 포함 요소

- Manual PDF
- Text extraction
- Image extraction
- BGE-M3 embedding
- SigLIP-based text-image similarity signal
- ChromaDB
- G2/G3/G4 retrieval
- Ollama local LLM
- Answer and image evidence

### 논문 위치

Proposed Framework 첫 부분

## Figure 2. 전처리 및 인덱싱 파이프라인

### 목적

텍스트와 이미지가 어떤 방식으로 분리 추출되고 다시 연결되는지 설명한다.

### 포함 요소

- PDF page
- text chunk
- extracted image
- page metadata
- nearby text
- text-image mapping score
- vector DB indexing

### 논문 위치

Preprocessing 또는 Dataset Construction

## Figure 3. G3 멀티모달 검색 구조

### 목적

G3가 단순 이미지 검색이 아니라 여러 점수를 결합한다는 점을 보여준다.

### 포함 요소

- text retrieval score
- image retrieval score
- page proximity
- text-image mapping score
- final image ranking

### 논문 위치

Multimodal Retrieval Method

## Figure 4. G4 Context-aware Re-ranking 구조

### 목적

G4가 G3에서 무엇을 추가했는지 명확히 보여준다.

### 포함 요소

- G3 candidate list
- automatic stage classification
- stage context map
- page range match
- section/keyword match
- re-ranked text/image candidates

### 논문 위치

Context-aware Re-ranking Method

## Figure 5. G1/G2/G3/G4 검색 성능 비교 그래프

### 목적

정량 결과에서 G4의 개선점을 시각적으로 보여준다.

### 권장 그래프

- Text Recall@1/5/10 grouped bar chart
- Image Recall@1/5/10 grouped bar chart
- Image MRR bar chart
- Both@5/Both@10 bar chart

### 강조 포인트

- G4 Image Recall@5: 75.7%
- G4 Image Recall@10: 87.1%
- G4 Image MRR: 0.539

## Figure 6. G4 개선 사례

### 목적

정량 결과뿐 아니라 실제 검색 순위가 어떻게 개선되었는지 보여준다.

### 후보 사례

| 질문 | G3 순위 | G4 순위 | 정답 이미지 |
|---|---:|---:|---|
| Q31 티치 펜던트/USB 데이터 관리 | Top-10 밖 | 3위 | `page_103_img_0_0.jpeg` |
| Q23 UI/시스템 정보 확인 | Top-10 밖 | 5위 | `page_167_img_3_0.jpeg` |
| Q02 안전/전원/접지 | Top-10 밖 | 5위 | `page_403_img_0_0.jpeg` |

### 논문 위치

Results and Discussion

## Figure 7. G4 실패 사례

### 목적

동일 page 또는 동일 section 내 유사 이미지 구분 한계를 설명한다.

### 후보 사례

| 질문 | 문제 |
|---|---|
| Q10 티치 펜던트 상태 확인 | 관련 Status 범위는 맞지만 정답 화면 이미지 누락 |
| Q28 케이블 방수 | 같은 page의 다른 이미지는 검색되었지만 정확한 이미지 실패 |
| Q15 시스템 관리/로그 | 자동 단계 분류가 UI/시스템 정보 확인으로 치우침 |

### 논문 위치

Discussion 또는 Limitations

## 필수 표 목록

| 표 | 내용 | 관련 파일 |
|---|---|---|
| Table 1 | 질의셋 구성 | `03_question_set_70.xlsx` |
| Table 2 | G1/G2/G3/G4 비교군 정의 | `26_experiment_pipeline.md` |
| Table 3 | 실험 환경 | `19_paper_draft.md` |
| Table 4 | 검색 성능 결과 | `15_g1_g2_g3_g4_summary.xlsx` |
| Table 5 | 응답 품질 평가 결과 | `22_response_quality_eval_summary.xlsx` |
| Table 6 | G4 개선/실패 사례 | `16_g4_case_analysis.md` |

## 우선 제작 순서

1. Figure 1 전체 시스템 아키텍처
2. Figure 4 G4 context-aware re-ranking 구조
3. Figure 5 검색 성능 비교 그래프
4. Figure 6 G4 개선 사례
5. Figure 7 G4 실패 사례

초기 교수님 보고용으로는 Figure 1, Figure 4, Figure 5만 먼저 만들어도 충분하다.
