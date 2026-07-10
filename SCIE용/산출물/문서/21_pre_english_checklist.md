# 영문화 전 보강 체크리스트

## 완료된 보강

| 항목 | 상태 | 관련 파일 |
|---|---|---|
| 논문용 최종 정리본 작성 | 완료 | `18_paper_ready_summary.md` |
| 국문 논문 초안 작성 | 완료 | `19_paper_draft.md` |
| RAG / retrieval 관련 참고문헌 반영 | 완료 | `19_paper_draft.md`, `20_reference_candidates.md` |
| CLIP / SigLIP / BGE-M3 관련 참고문헌 반영 | 완료 | `19_paper_draft.md`, `20_reference_candidates.md` |
| Qwen / Gemma / Llama / QLoRA 참고문헌 후보 정리 | 완료 | `20_reference_candidates.md` |
| 협동 로봇 실습 교육 참고문헌 후보 정리 | 완료 | `20_reference_candidates.md` |
| 실험 환경 표 추가 | 완료 | `19_paper_draft.md` |
| 로컬 LLM 모델 표 추가 | 완료 | `19_paper_draft.md` |
| Qwen/Gemma/Llama 응답 생성 및 rubric 기반 1차 평가 | 완료 | `22_response_quality_eval_results.md`, `excel/22_response_quality_eval_results.xlsx` |
| 연구자 검토용 체크리스트 생성 | 완료 | `31_researcher_review_checklist.md`, `excel/31_researcher_review_checklist.xlsx` |
| G4 우선 검토 대상 연구자 수동 검토 | 완료 | `31_researcher_review_checklist.md`, `excel/31_researcher_review_checklist.xlsx` |
| G4 context map 구축 절차 정리 | 완료 | `33_context_map_protocol.md` |
| 논문 표/그림 캡션 초안 작성 | 완료 | `32_tables_figures_captions.md` |
| IEEE Access 준비 체크리스트 작성 | 완료 | `34_ieee_access_readiness_checklist.md` |
| strict / relaxed 텍스트 평가 기준 정책 정리 | 완료 | `35_text_evaluation_policy.md` |
| 시스템 전체 초심자용 설명서 작성 | 완료 | `36_system_full_explanation.md` |

## 영문화 전 아직 필요한 작업

| 우선순위 | 항목 | 필요 이유 |
|---:|---|---|
| 1 | 관련 연구 참고문헌 최종 서지정보 정리 | IEEE 양식으로 변환하기 전 저자, 학회, 연도 확인 필요 |
| 2 | 그림/도식 실제 제작 | 전체 프레임워크, G4 re-ranking 구조, 검색 성능 그래프 필요 |
| 3 | 영문 초안 변환 | IEEE Access 문체와 구조로 변환 필요 |

## 현재 상태 판단

현재 상태에서 영문 초안으로 바로 옮길 수 있는 부분은 다음과 같다.

- Abstract 초안
- Introduction 초안
- Related Work 초안
- Proposed Framework 초안
- Experimental Setup 초안
- Retrieval Results and Discussion 초안
- Response Quality Evaluation 초안
- Conclusion 초안

아직 영문 원고에서 결과로 확정하기 어려운 부분은 다음과 같다.

- 사용자 평가 또는 전문가 평가 결과
- strict 평가 결과

따라서 다음 단계는 문서 작업 중심으로 진행한다. 우선 참고문헌 서지정보를 IEEE 양식으로 정리하고, Figure 1/4/5를 제작한 뒤, `19_paper_draft.md`를 IEEE Access 스타일 영문 초안으로 변환한다.
