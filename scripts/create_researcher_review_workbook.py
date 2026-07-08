import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import SCIE_DATA_DIR, SCIE_DIR, SCIE_EXCEL_DIR  # noqa: E402


RESPONSE_RESULTS_PATH = SCIE_DATA_DIR / "22_response_quality_eval_results.csv"
G4_RETRIEVAL_PATH = SCIE_DATA_DIR / "30_g4_auto_retrieval_results.csv"

OUTPUT_CSV_PATH = SCIE_DATA_DIR / "31_researcher_review_checklist.csv"
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "31_researcher_review_checklist.xlsx"
OUTPUT_MD_PATH = SCIE_DIR / "31_researcher_review_checklist.md"

CASE_IDS = {
    "Q02": "G4 개선 사례: 안전/전원/접지",
    "Q23": "G4 개선 사례: UI/시스템 정보 확인",
    "Q31": "G4 개선 사례: 티치 펜던트/USB 데이터 관리",
    "Q10": "G4 실패 사례: 티치 펜던트/상태 확인",
    "Q15": "G4 실패 사례: 시스템 관리/로그",
    "Q28": "G4 실패 사례: 설치/케이블 방수",
}

FIELDS = [
    "검토 번호",
    "검토 유형",
    "우선순위",
    "질문 번호",
    "비교군",
    "모델",
    "질문",
    "실습 단계",
    "정답 텍스트",
    "정답 이미지",
    "검색 텍스트 순위",
    "검색 이미지 순위",
    "자동 정확성(1-5)",
    "자동 구체성(1-5)",
    "자동 실습 단계 적합성(1-5)",
    "자동 안전성(1-5)",
    "자동 이해 용이성(1-5)",
    "자동 평균 점수",
    "자동 최종 판정",
    "자동 평가 메모",
    "모델 답변",
    "연구자 정확성(1-5)",
    "연구자 구체성(1-5)",
    "연구자 실습 단계 적합성(1-5)",
    "연구자 안전성(1-5)",
    "연구자 이해 용이성(1-5)",
    "연구자 최종 판정(O/△/X)",
    "검토 완료(Y/N)",
    "수정/비고",
]


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_dicts(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def priority_for(row, reason):
    if row["최종 판정(O/△/X)"] == "X":
        return "상"
    if "실패 사례" in reason:
        return "상"
    if row["모델"] == "Qwen" and row["비교군"] == "G4":
        return "중"
    return "중"


def add_review_row(rows, source_row, reason, seen):
    key = (source_row["질문 번호"], source_row["비교군"], source_row["모델"], reason)
    if key in seen:
        return
    seen.add(key)

    rows.append(
        {
            "검토 번호": f"R{len(rows) + 1:03d}",
            "검토 유형": reason,
            "우선순위": priority_for(source_row, reason),
            "질문 번호": source_row["질문 번호"],
            "비교군": source_row["비교군"],
            "모델": source_row["모델"],
            "질문": source_row["질문"],
            "실습 단계": source_row["실습 단계"],
            "정답 텍스트": source_row["정답 텍스트"],
            "정답 이미지": source_row["정답 이미지"],
            "검색 텍스트 순위": source_row["검색 텍스트 순위"],
            "검색 이미지 순위": source_row["검색 이미지 순위"],
            "자동 정확성(1-5)": source_row["정확성(1-5)"],
            "자동 구체성(1-5)": source_row["구체성(1-5)"],
            "자동 실습 단계 적합성(1-5)": source_row["실습 단계 적합성(1-5)"],
            "자동 안전성(1-5)": source_row["안전성(1-5)"],
            "자동 이해 용이성(1-5)": source_row["이해 용이성(1-5)"],
            "자동 평균 점수": source_row["평균 점수"],
            "자동 최종 판정": source_row["최종 판정(O/△/X)"],
            "자동 평가 메모": source_row["평가 메모"],
            "모델 답변": source_row["모델 답변"],
            "연구자 정확성(1-5)": "",
            "연구자 구체성(1-5)": "",
            "연구자 실습 단계 적합성(1-5)": "",
            "연구자 안전성(1-5)": "",
            "연구자 이해 용이성(1-5)": "",
            "연구자 최종 판정(O/△/X)": "",
            "검토 완료(Y/N)": "",
            "수정/비고": "",
        }
    )


def build_rows():
    response_rows = read_csv_dicts(RESPONSE_RESULTS_PATH)
    g4_retrieval_rows = {row["질문 번호"]: row for row in read_csv_dicts(G4_RETRIEVAL_PATH)}

    selected = []
    seen = set()

    for row in response_rows:
        if row["비교군"] == "G4" and row["최종 판정(O/△/X)"] == "X":
            add_review_row(selected, row, "G4 응답 X 판정 전체 검토", seen)

    for row in response_rows:
        if row["비교군"] == "G4" and row["모델"] == "Qwen" and row["최종 판정(O/△/X)"] == "△":
            add_review_row(selected, row, "G4-Qwen △ 판정 검토", seen)

    for question_id, reason in CASE_IDS.items():
        for row in response_rows:
            if row["질문 번호"] == question_id and row["비교군"] == "G4" and row["모델"] == "Qwen":
                retrieval = g4_retrieval_rows.get(question_id, {})
                enriched = dict(row)
                if retrieval:
                    enriched["검색 이미지 순위"] = retrieval.get("G4 이미지 정답 순위", row["검색 이미지 순위"])
                add_review_row(selected, enriched, reason, seen)

    return selected


def write_report(rows):
    total = len(rows)
    high = sum(1 for row in rows if row["우선순위"] == "상")
    by_reason = {}
    for row in rows:
        by_reason[row["검토 유형"]] = by_reason.get(row["검토 유형"], 0) + 1

    lines = [
        "# 연구자 검토 체크리스트",
        "",
        "## 목적",
        "",
        "이 문서는 응답 품질 평가를 논문에 사용할 때 사람이 확인해야 할 대표 사례를 정리한 검토표이다.",
        "현재 자동 평가는 AI-assisted rubric 기반 1차 평가이므로, 이 표의 `연구자 ...` 열을 사람이 직접 확인해야 연구자 검토 결과로 사용할 수 있다.",
        "",
        "## 검토 대상 선정 기준",
        "",
        "- G4 응답 중 X 판정 전체",
        "- G4-Qwen 응답 중 △ 판정",
        "- G4 개선 사례 3개와 실패 사례 3개",
        "",
        "## 요약",
        "",
        f"- 전체 검토 대상: {total}개",
        f"- 우선순위 상: {high}개",
        "",
        "| 검토 유형 | 건수 |",
        "|---|---:|",
    ]
    for reason, count in sorted(by_reason.items()):
        lines.append(f"| {reason} | {count} |")

    lines.extend(
        [
            "",
            "## 검토 방법",
            "",
            "1. `모델 답변`이 `정답 텍스트`의 핵심 내용을 포함하는지 확인한다.",
            "2. 메뉴명, 수치, 절차, 안전 관련 표현이 틀리지 않았는지 확인한다.",
            "3. 자동 점수가 과도하게 높거나 낮으면 `연구자 ...` 점수에 수정 점수를 입력한다.",
            "4. 검토가 끝난 행은 `검토 완료(Y/N)`에 `Y`를 입력한다.",
            "5. 논문에는 자동 평가와 연구자 검토를 구분해서 서술한다.",
            "",
            "## 산출 파일",
            "",
            f"- `{OUTPUT_CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{OUTPUT_XLSX_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        ]
    )
    OUTPUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = build_rows()
    write_csv_dicts(OUTPUT_CSV_PATH, rows)
    write_workbook([FIELDS] + [[row.get(field, "") for field in FIELDS] for row in rows], OUTPUT_XLSX_PATH, "연구자 검토표")
    write_report(rows)
    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {OUTPUT_MD_PATH}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
