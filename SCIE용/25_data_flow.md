# 데이터 흐름 문서

## 목적

본 문서는 원본 매뉴얼에서 최종 평가 결과까지 데이터가 어떻게 이동하고 변환되는지 설명한다. 논문에서는 Dataset, Preprocessing, Experimental Setup 섹션에 활용할 수 있다.

## 전체 데이터 흐름

```text
data/raw/A-Series.pdf
        |
        v
PDF 텍스트/이미지 추출
        |
        +--> data/processed/text_chunks.json
        +--> data/processed/final_refined_data/
        +--> data/processed/*processing_report.json
        |
        v
임베딩 및 매핑 생성
        |
        +--> data/vector_db/rag_db/
        +--> data/processed/text_image_mapping_report.json
        |
        v
평가 질의셋 구성
        |
        +--> SCIE용/data/03_question_set_70.csv
        +--> SCIE용/excel/03_question_set_70.xlsx
        |
        v
G1/G2/G3/G4 검색 평가
        |
        +--> SCIE용/data/15_g1_g2_g3_g4_summary.csv
        +--> SCIE용/excel/15_g1_g2_g3_g4_summary.xlsx
        +--> SCIE용/data/15_g1_g2_g3_g4_retrieval_results.csv
        |
        v
응답 품질 평가
        |
        +--> SCIE용/data/22_response_quality_eval_results.csv
        +--> SCIE용/excel/22_response_quality_eval_results.xlsx
```

## 원본 데이터

| 데이터 | 설명 |
|---|---|
| `data/raw/A-Series.pdf` | 협동 로봇 실습 매뉴얼 원본 |
| Doosan DART-Platform Manual | 매뉴얼 구조와 section/page 기준의 근거 자료 |

## 전처리 산출물

| 파일/폴더 | 설명 |
|---|---|
| `data/processed/text_chunks.json` | 검색 단위로 분할된 텍스트 chunk |
| `data/processed/final_refined_data/` | 최종 이미지/도식 파일 |
| `data/processed/final_processing_report.json` | 이미지 처리 결과 보고 |
| `data/processed/text_image_mapping_report.json` | 텍스트-이미지 매핑 및 similarity 정보 |

## 인덱싱 산출물

| 파일/폴더 | 설명 |
|---|---|
| `data/vector_db/rag_db/` | ChromaDB 기반 텍스트/이미지 검색 인덱스 |
| `models/hf_cache/` | BGE-M3, SigLIP 관련 모델 캐시 |
| `models/siglip_local/` | 로컬 SigLIP 모델 파일 |
| `runtime/ollama_models/` | 로컬 LLM 모델 파일 |

## 평가 데이터

| 파일 | 설명 |
|---|---|
| `03_question_set_70.csv/xlsx` | 70개 질의셋, 정답 텍스트, 정답 이미지, 실습 단계 라벨 |
| `11_stage_context_map_manual.csv/xlsx` | G4용 실습 단계 context map |
| `15_g1_g2_g3_g4_summary.csv/xlsx` | G1/G2/G3/G4 검색 성능 요약 |
| `15_g1_g2_g3_g4_retrieval_results.csv/xlsx` | 질문별 검색 상세 결과 |
| `22_response_quality_eval_summary.csv/xlsx` | 응답 품질 평가 요약 |
| `22_response_quality_eval_results.csv/xlsx` | 630개 모델 응답과 채점 결과 |

## 논문용 최종 데이터 기준

논문에서 최종 결과로 사용할 데이터는 다음이다.

| 목적 | 파일 |
|---|---|
| 질의셋 | `산출물/엑셀/03_question_set_70.xlsx` |
| G4 context map | `산출물/엑셀/11_stage_context_map_manual.xlsx` |
| 검색 성능 요약 | `산출물/엑셀/15_g1_g2_g3_g4_summary.xlsx` |
| 검색 상세 결과 | `산출물/엑셀/15_g1_g2_g3_g4_retrieval_results.xlsx` |
| 응답 품질 요약 | `산출물/엑셀/22_response_quality_eval_summary.xlsx` |
| 응답 품질 상세 결과 | `산출물/엑셀/22_response_quality_eval_results.xlsx` |

## 제외할 데이터

다음 파일들은 실험 과정 기록 또는 예비 실험이므로 최종 논문 결과로 직접 사용하지 않는다.

- `09_stage_context_map.*`
- `10_g4_results.*`
- `08_context_image_retrieval_results.*`

다만 연구 진행 과정 설명이나 내부 기록에는 참고할 수 있다.
