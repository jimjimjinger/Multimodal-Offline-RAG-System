# IEEE Access 원고 준비 체크리스트

## 목적

이 문서는 현재 SCIE/IEEE Access 원고로 전환하기 전에 남은 작업을 구분하기 위한 체크리스트이다. 연구자 검토 완료 항목과, 앞으로 남은 문서/표/그림 작성 항목을 분리한다.

## 현재 완료된 항목

| 항목 | 상태 | 관련 파일 |
|---|---|---|
| 연구 질문 정리 | 완료 | `04_research_questions.md` |
| G1/G2/G3/G4 비교군 정의 | 완료 | `05_experiment_groups.md`, `26_experiment_pipeline.md` |
| 평가 지표 정의 | 완료 | `06_metrics.md`, `27_evaluation_protocol.md` |
| 70개 질의셋 구성 | 완료 | `excel/03_question_set_70.xlsx` |
| G4 stage context map 구축 | 완료 | `excel/11_stage_context_map_manual.xlsx`, `33_context_map_protocol.md` |
| G4 질문 기반 단계 추정 구현 및 평가 | 완료 | `29_stage_classifier_results.md` |
| G1/G2/G3/G4 검색 성능 평가 | 완료 | `15_g1_g2_g3_g4_results.md` |
| G4 개선/실패 사례 분석 | 완료 | `16_g4_case_analysis.md` |
| 응답 품질 rubric 기반 1차 평가 | 완료 | `22_response_quality_eval_results.md` |
| 연구자 검토용 체크리스트 생성 | 완료 | `31_researcher_review_checklist.md` |
| G4 우선 검토 대상 연구자 검토 | 완료 | `31_researcher_review_checklist.md`, `excel/31_researcher_review_checklist.xlsx` |
| 국문 논문 초안 작성 | 완료 | `19_paper_draft.md` |
| 참고문헌 후보 정리 | 완료 | `20_reference_candidates.md` |
| 표/그림 캡션 초안 작성 | 완료 | `32_tables_figures_captions.md` |

## 지민이 나중에 직접 해야 하는 항목

| 우선순위 | 항목 | 이유 | 파일 |
|---:|---|---|---|
| 1 | 대표 사례 이미지 육안 확인 | 논문에 사례 그림을 넣을 때 실제 이미지가 질문과 맞는지 확인 필요 | `data/processed/final_refined_data/` |
| 2 | 교수님에게 보여줄 최종 보고 파일 선택 | 보고 분량 조절 필요 | `SCIE용/산출물/` |

## 제가 이어서 할 수 있는 항목

| 우선순위 | 항목 | 설명 |
|---:|---|---|
| 1 | 영문 초안 변환 | `19_paper_draft.md`를 IEEE Access 스타일 영문 초안으로 변환 |
| 2 | Figure 1/4 구조도 제작 | 시스템 아키텍처와 G4 re-ranking 구조 도식화 |
| 3 | Figure 5 성능 비교 그래프 제작 | G1-G4 검색 성능 결과를 그래프로 시각화 |
| 4 | 참고문헌 IEEE 형식 정리 | 현재 후보 문헌을 IEEE reference style로 정리 |
| 5 | Abstract/Introduction 압축 | IEEE Access 원고 길이에 맞게 중복 표현 축소 |

## 원고에서 조심해야 할 표현

| 피해야 할 표현 | 이유 | 대체 표현 |
|---|---|---|
| 전체 630개 응답을 전문가가 모두 재채점했다 | 연구자 검토는 G4 우선 검토 대상 54개에 대해 수행됨 | AI-assisted rubric-based evaluation on 630 responses, supplemented by researcher review of 54 priority G4 cases |
| G4가 응답 품질을 크게 개선했다 | 최신 결과에서 G4-Qwen은 G3-Qwen보다 소폭 낮음 | G4 improved retrieval performance while maintaining comparable response quality |
| 이미지 검색 문제가 해결되었다 | Image R@1은 아직 37.1% | G4 improved image retrieval ranking but still has limitations in image-level discrimination |
| 8GB 이하 환경에서 검증했다 | 정량 실험은 24GB 개발 노트북에서 수행 | The system is designed for resource-constrained local deployment, while full quantitative evaluation was conducted on a development laptop |
| CLIP을 사용했다 | 실제 구현은 SigLIP 기반 신호 사용 | CLIP is discussed as related work; SigLIP is used for image-text similarity signals |

## 영문 원고 권장 구조

1. Introduction
2. Related Work
3. Proposed Framework
4. Dataset and Experimental Setup
5. Results
6. Discussion
7. Limitations
8. Conclusion

## 다음 작업 추천 순서

1. 참고문헌을 IEEE 양식으로 정리한다.
2. Figure 1/4/5를 제작한다.
3. `19_paper_draft.md`를 IEEE Access 스타일 영문 초안으로 변환한다.
4. 대표 사례 이미지를 육안 확인하고 논문용 그림으로 정리한다.
5. IEEE Access 템플릿에 맞춰 원고를 옮긴다.
