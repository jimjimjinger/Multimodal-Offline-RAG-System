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

## 폴더 구조

| 폴더 | 용도 |
|---|---|
| `data/` | 코드 실행과 평가에 사용하는 CSV 원본 데이터 |
| `excel/` | 사람이 확인하기 쉬운 XLSX 파일 |
| 루트 | 보고서와 정리 문서 Markdown 파일 |
