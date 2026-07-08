# SCIE 논문 준비 폴더

## 목표

교수님 피드백에 따라 시스템 기능 추가보다 실험 가능한 구조를 먼저 확정한다.
핵심은 텍스트 기반 RAG와 멀티모달 RAG를 비교하여 검색 성능과 응답 품질 차이를 검증하는 것이다.

## 진행 순서

1. SCIE 논문용 연구 질문 확정
2. 데이터셋과 질의셋 구성 정리
3. 실습 단계 라벨링
4. 비교군 확정
5. 평가 지표 확정
6. 1차 파일럿 실험 결과 정리
7. Method 초안 작성
8. Experiments 초안 작성

## 현재 진행 상태

| 단계 | 산출물 | 상태 |
|---|---|---|
| 질의셋 라벨링 | data/01_question_stage_labels.csv, excel/01_question_stage_labels.xlsx | 진행 완료 |
| 라벨 요약 | 01_stage_label_summary.md | 진행 완료 |
| 질의셋 확장 | data/02_additional_questions_32.csv, excel/02_additional_questions_32.xlsx | 진행 완료 |
| 통합 질의셋 | data/03_question_set_70.csv, excel/03_question_set_70.xlsx | 진행 완료 |
| 연구 질문 | 04_research_questions.md | 진행 완료 |
| 비교군 | 05_experiment_groups.md | 진행 완료 |
| 평가 지표 | 06_metrics.md | 진행 완료 |
| 파일럿 결과 | 07_pilot_results.md | 진행 완료 |
| 상황 인지형 G4 개선 설계 | 08_context_rerank_results.md | 작성 완료 |
| G1/G2/G3/G4 비교 결과 | 15_g1_g2_g3_g4_results.md | 진행 완료 |
| G4 개선/실패 사례 분석 | 16_g4_case_analysis.md | 진행 완료 |
| 응답 품질 평가 기준 | 17_response_quality_eval_criteria.md, excel/17_response_quality_eval_template.xlsx | 진행 완료 |
| 논문용 최종 정리본 | 18_paper_ready_summary.md | 작성 완료 |
| 논문 초안 | 19_paper_draft.md | 1차 작성 완료 |
| 참고문헌 후보 정리 | 20_reference_candidates.md | 작성 완료 |
| 영문화 전 보강 체크리스트 | 21_pre_english_checklist.md | 작성 완료 |
| 응답 품질 평가 결과 | 22_response_quality_eval_results.md, excel/22_response_quality_eval_results.xlsx | 자동 1차 평가 완료 |
| G4 단계 자동 분류 | 29_stage_classifier_results.md, excel/29_stage_classifier_eval.xlsx | 진행 완료 |
| 자동분류 기반 G4 검색 결과 | 30_g4_auto_results.md, excel/30_g4_auto_retrieval_results.xlsx | 진행 완료 |
| 최종 산출물 폴더 | 산출물/00_산출물_목록.md | 정리 완료 |

## 폴더 구조

| 폴더 | 용도 |
|---|---|
| `data/` | 코드 실행과 평가에 사용하는 CSV 원본 데이터 |
| `excel/` | 사람이 확인하기 쉬운 XLSX 파일 |
| 루트 | 보고서와 정리 문서 Markdown 파일 |
| `산출물/` | 논문/보고에 직접 사용할 최종 산출물 모음 |
