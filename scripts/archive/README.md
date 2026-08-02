# Archived SCIE Scripts

이 폴더의 스크립트는 현재 논문 본 실험의 최종 실행 경로가 아닙니다.

- `evaluate_scie_g4_retrieval.py`: 정답 실습 단계를 직접 넣어 평가한 oracle/manual G4 실험용 코드입니다.
- `evaluate_scie_context_rerank.py`: 정식 G4 구현 전 단계 라벨만 넣어 본 파일럿 코드입니다.
- `evaluate_scie_image_retrieval.py`: 초기 이미지 검색 단독 평가 코드입니다.
- `create_scie_context_map.py`: 질의셋 기반 초안 context map 생성 코드입니다.
- `create_g4_context_review.py`: manual/oracle G4 검토표 생성 코드입니다.
- `apply_g4_manual_overrides.py`: manual context map 보정용 일회성 코드입니다.

최종 비교 실험은 `scripts/evaluate_stage_classifier.py`,
`scripts/evaluate_scie_g4_auto_retrieval.py`, `scripts/evaluate_scie_all_groups.py`,
`scripts/evaluate_response_quality.py`를 기준으로 실행합니다.
