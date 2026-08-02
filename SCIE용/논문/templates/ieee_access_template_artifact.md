# IEEE Access Word 템플릿 적용 명세

## Reference

- 원본: `SCIE용/논문/templates/Access-Template-2024.docx`
- 공식 배포 URL: `https://ieeeaccess.ieee.org/wp-content/uploads/2025/08/Access-Template-2024.docx`
- SHA-256: `C30433CE4E817BF4FBA6DC69E6E4D5BF7FC1F8E7B0126374C65926DBD5D5B1BB`
- 원본 페이지 수: 8
- 원본 섹션 수: 9
- 시각 검수: 전체 8페이지 PDF 변환 및 PNG 렌더링 확인

## Page System

- 용지: 8.00 x 10.88 inch, 세로
- 여백: 왼쪽 0.51, 오른쪽 0.51, 위 0.89~0.90, 아래 0.72 inch
- 전면부: 제목, 저자, 초록, Index Terms를 한 단으로 배치
- 본문: 연속 구역 나누기 이후 2단, 단 사이 400 DXA
- 그림·폭이 넓은 표·Algorithm 1: 가독성을 위해 연속 구역 나누기로 한 단 배치 후 2단으로 복귀
- 헤더·푸터: 원본 IEEE Access 로고, 구분선 및 페이지 필드 구조를 유지

## Typography

| 역할 | 템플릿 스타일 | 주요 속성 |
|---|---|---|
| 논문 제목 | `Paper Title` | Helvetica 22 pt, bold, IEEE blue |
| 저자 | `AU` | Helvetica 10 pt, bold |
| 소속 | `PI_No Space`, `PI` | 7.5 pt 계열 |
| 초록 | `Abstract` | 10 pt, 양쪽 정렬 |
| 색인어 | `IT` | 10 pt |
| 1단계 제목 | `H1_List (Space)` | 파란색 IEEE 절 제목 |
| 2단계 제목 | `H2_First`, `H2_Cont` | Helvetica 9 pt, bold italic, gray |
| 본문 | `PARA`, `PARA_Indent` | 10 pt, 양쪽 정렬 |
| 그림 캡션 | `Figure Caption` 계열 | 템플릿 캡션 스타일 우선 |
| 참고문헌 | `References` | 8 pt, 내어쓰기 |

## Editable Slots

- 출판일·DOI: 제출 전 미정 상태로 유지
- 제목: 확정 영문 제목
- 저자·소속·교신저자: 현재 정보가 없어 명시적 자리표시자로 유지
- 초록·Index Terms: 영문 초안의 확정 문단
- 본문: Introduction부터 Conclusion까지
- 그림: 검수된 Figure 1, Figure 2 PNG
- 알고리즘: Algorithm 1의 입력·출력·의사코드·기호 설명
- 표: 비교군, 평가 기준, BBox/SigLIP, 환경, 모델, G1~G4 결과 및 응답 품질
- 참고문헌: 본문에서 실제 인용한 30편
- 저자 약력: 저자 정보가 없어 제출 전 입력 자리표시자로 유지

## Preservation Rules

- 공식 템플릿 원본은 수정하지 않는다.
- 최종 통합본은 원본의 복사본에서 생성한다.
- 스타일, 테마, IEEE Access 로고, 헤더·푸터 관계를 가능한 범위에서 유지한다.
- 기존 안내 문구, 예시 표·그림·참고문헌·저자 사진은 제거하고 연구 원고로 대체한다.
- 사용자에게 확인되지 않은 저자명, 소속, ORCID, 연구비 및 약력을 임의로 작성하지 않는다.

## Fidelity Gates

1. 본문이 2단 단일 간격 형식인지 확인한다.
2. Figure 1과 Figure 2의 글자가 실제 페이지 크기에서 읽히는지 확인한다.
3. 표, 캡션, Algorithm 1이 열 경계에서 잘리거나 겹치지 않는지 확인한다.
4. 참고문헌 30편과 본문 인용 번호가 일치하는지 확인한다.
5. 모든 페이지를 PNG로 렌더링하여 잘림, 빈 페이지, 겹침 및 누락을 검사한다.
