import csv
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import SCIE_DATA_DIR, SCIE_DIR, SCIE_EXCEL_DIR  # noqa: E402


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
G3_RESULT_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
MANUAL_MAP_PATH = SCIE_DATA_DIR / "11_stage_context_map_manual.csv"
MANUAL_RESULT_PATH = SCIE_DATA_DIR / "12_g4_manual_retrieval_results.csv"
OUTPUT_CSV_PATH = SCIE_DATA_DIR / "14_g4_context_review.csv"
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "14_g4_context_review.xlsx"
OUTPUT_MD_PATH = SCIE_DIR / "14_g4_context_review.md"


FIELDS = [
    "검토 판정",
    "질문 번호",
    "실습 단계",
    "질문",
    "정답 이미지",
    "정답 이미지 페이지",
    "G3 이미지 순위",
    "G4 수동 이미지 순위",
    "G4 수동 이미지 평가",
    "현재 텍스트 페이지 범위",
    "현재 이미지 페이지 범위",
    "정답 이미지 페이지 포함 여부",
    "본문 키워드",
    "근거",
    "수정 제안",
]


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def image_page(value):
    match = re.search(r"page_(\d+)_", str(value or ""))
    return int(match.group(1)) if match else None


def parse_ranges(value):
    ranges = []
    for part in str(value or "").split(";"):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if match:
            start, end = sorted((int(match.group(1)), int(match.group(2))))
            ranges.append((start, end))
            continue
        for page in re.findall(r"\d+", part):
            value = int(page)
            ranges.append((value, value))
    return ranges


def page_in_ranges(page, ranges):
    if page is None:
        return False
    return any(start <= page <= end for start, end in ranges)


def rank(value):
    value = str(value or "").strip()
    return int(value) if value.isdigit() else None


def review_status(g3_rank, g4_rank, contains_answer_page):
    if g4_rank is None:
        return "필수 검토"
    if g4_rank > 10:
        return "필수 검토"
    if not contains_answer_page:
        return "범위 검토"
    if g3_rank and g4_rank > g3_rank:
        return "순위 하락 검토"
    if g4_rank > 5:
        return "Top-5 개선 검토"
    return "유지 후보"


def suggestion(stage, contains_answer_page, g4_rank):
    stage_text = stage.lower()
    suggestions = []
    if not contains_answer_page:
        suggestions.append("현재 이미지 페이지 범위에 정답 이미지 page가 없으므로 section/page 범위 재검토")
    if any(term in stage for term in ["설치", "설정", "좌표", "안전", "전원"]):
        suggestions.append("넓은 키워드보다 섹션명, 부품명, 핀명, 명령어명 등 구체 키워드 우선")
    if "TCP".lower() in stage_text or "좌표" in stage:
        suggestions.append("TCP/Tool Settings와 Safety Zone 좌표계가 혼동되지 않도록 섹션 우선순위 분리")
    if "I/O".lower() in stage_text or "io" in stage_text:
        suggestions.append("TBSFT/TBCI/TBCO/TBPWR 등 단자블록명 기준으로 세부 단계 분리")
    if g4_rank is None:
        suggestions.append("후보 수집 범위 또는 stage keyword를 확장해 Top-10 안에 포함되도록 조정")
    elif g4_rank > 5:
        suggestions.append("정답 후보가 Top-5 밖이면 page prior보다 section/keyword prior를 강화")
    return " / ".join(suggestions) if suggestions else "현재 매핑 유지 가능"


def main():
    questions = {row["질문 번호"]: row for row in read_csv_dicts(QUESTION_SET_PATH)}
    g3_rows = {row["질문 번호"]: row for row in read_csv_dicts(G3_RESULT_PATH)}
    manual_rows = {row["실습 단계"]: row for row in read_csv_dicts(MANUAL_MAP_PATH)}
    result_rows = read_csv_dicts(MANUAL_RESULT_PATH)

    output_rows = []
    for row in result_rows:
        qid = row["질문 번호"]
        stage = row["실습 단계"]
        question = questions.get(qid, {})
        mapping = manual_rows.get(stage, {})
        g3 = g3_rows.get(qid, {})

        answer_image = row["정답 이미지"]
        answer_page = image_page(answer_image)
        image_ranges = parse_ranges(mapping.get("이미지 페이지 범위", ""))
        contains_page = page_in_ranges(answer_page, image_ranges)
        g3_image_rank = rank(g3.get("이미지 정답 순위"))
        g4_image_rank = rank(row.get("G4 이미지 정답 순위"))
        status = review_status(g3_image_rank, g4_image_rank, contains_page)

        output_rows.append(
            {
                "검토 판정": status,
                "질문 번호": qid,
                "실습 단계": stage,
                "질문": row["질문"],
                "정답 이미지": answer_image,
                "정답 이미지 페이지": answer_page or "",
                "G3 이미지 순위": g3.get("이미지 정답 순위", ""),
                "G4 수동 이미지 순위": row.get("G4 이미지 정답 순위", ""),
                "G4 수동 이미지 평가": row.get("G4 이미지 평가", ""),
                "현재 텍스트 페이지 범위": mapping.get("텍스트 페이지 범위", ""),
                "현재 이미지 페이지 범위": mapping.get("이미지 페이지 범위", ""),
                "정답 이미지 페이지 포함 여부": "포함" if contains_page else "미포함",
                "본문 키워드": mapping.get("본문 키워드", ""),
                "근거": mapping.get("근거", ""),
                "수정 제안": suggestion(stage, contains_page, g4_image_rank),
            }
        )

    priority = {
        "필수 검토": 0,
        "범위 검토": 1,
        "순위 하락 검토": 2,
        "Top-5 개선 검토": 3,
        "유지 후보": 4,
    }
    output_rows.sort(key=lambda item: (priority.get(item["검토 판정"], 9), item["질문 번호"]))

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    table = [FIELDS] + [[row.get(field, "") for field in FIELDS] for row in output_rows]
    write_workbook(table, OUTPUT_XLSX_PATH, "G4 매핑표 검토")

    counts = {}
    for row in output_rows:
        counts[row["검토 판정"]] = counts.get(row["검토 판정"], 0) + 1

    lines = [
        "# G4 매뉴얼 기준 매핑표 검토표",
        "",
        "## 목적",
        "",
        "`11_stage_context_map_manual`과 `12_g4_manual_retrieval_results`를 기준으로 사람이 검토해야 할 단계를 정리하였다.",
        "이 표는 매핑표를 자동으로 수정하기 위한 것이 아니라, 논문 본 실험 전에 어떤 단계의 page/section/keyword를 고정 검토해야 하는지 표시하기 위한 자료이다.",
        "",
        "## 검토 판정 요약",
        "",
        "| 판정 | 개수 |",
        "|---|---:|",
    ]
    for key in ["필수 검토", "범위 검토", "순위 하락 검토", "Top-5 개선 검토", "유지 후보"]:
        lines.append(f"| {key} | {counts.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            "- `SCIE용/data/14_g4_context_review.csv`",
            "- `SCIE용/excel/14_g4_context_review.xlsx`",
        ]
    )
    OUTPUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {OUTPUT_MD_PATH}")
    for key in ["필수 검토", "범위 검토", "순위 하락 검토", "Top-5 개선 검토", "유지 후보"]:
        print(f"{key}: {counts.get(key, 0)}")


if __name__ == "__main__":
    main()
