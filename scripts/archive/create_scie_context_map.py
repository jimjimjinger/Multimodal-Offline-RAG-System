import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import (  # noqa: E402
    SCIE_DATA_DIR,
    SCIE_DIR,
    SCIE_EXCEL_DIR,
    STAGE_CONTEXT_MAP_PATH,
    TEXT_CHUNKS_PATH,
    TEXT_IMAGE_MAPPING_REPORT_PATH,
)


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
OUTPUT_CSV_PATH = STAGE_CONTEXT_MAP_PATH
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "09_stage_context_map.xlsx"
OUTPUT_MD_PATH = SCIE_DIR / "09_stage_context_map.md"

TEXT_PAGE_RADIUS = 1
IMAGE_PAGE_RADIUS = 2
MAX_SECTION_KEYWORDS = 8
MAX_CONTENT_KEYWORDS = 14
MAX_ACTION_KEYWORDS = 10


STOPWORDS = {
    "그리고",
    "또는",
    "대한",
    "관련",
    "경우",
    "무엇",
    "어떤",
    "어떻게",
    "얼마",
    "사용",
    "설정",
    "입력",
    "확인",
    "기능",
    "항목",
    "위해",
    "위한",
    "에서",
    "으로",
    "로봇",
    "제어기",
    "컨트롤러",
    "두산로보틱스",
    "합니다",
    "있습니다",
    "됩니다",
}


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_pages(value):
    return [int(match) for match in re.findall(r"\d+", str(value or ""))]


def image_page_from_name(value):
    match = re.search(r"page_(\d+)_", str(value or ""))
    return int(match.group(1)) if match else None


def pages_from_chunk(chunk):
    pages = chunk.get("pages", [])
    if isinstance(pages, list):
        return [int(page) for page in pages if str(page).isdigit()]
    return parse_pages(pages)


def expand_pages(pages, radius):
    expanded = set()
    for page in pages:
        for value in range(page - radius, page + radius + 1):
            if value > 0:
                expanded.add(value)
    return expanded


def compact_ranges(pages):
    values = sorted({int(page) for page in pages if int(page) > 0})
    if not values:
        return ""

    ranges = []
    start = prev = values[0]
    for page in values[1:]:
        if page == prev + 1:
            prev = page
            continue
        ranges.append((start, prev))
        start = prev = page
    ranges.append((start, prev))

    return "; ".join(str(start) if start == end else f"{start}-{end}" for start, end in ranges)


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def tokenize(text):
    tokens = []
    for token in re.findall(r"[0-9A-Za-z가-힣]+", normalize(text).lower()):
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        if token.isdigit() and len(token) == 1:
            continue
        tokens.append(token)
    return tokens


def top_keywords(texts, max_terms):
    counter = Counter()
    for text in texts:
        counter.update(tokenize(text))

    keywords = []
    for term, _ in counter.most_common():
        if any(term in existing or existing in term for existing in keywords):
            continue
        keywords.append(term)
        if len(keywords) >= max_terms:
            break
    return keywords


def chunks_for_pages(chunks, target_pages):
    target_pages = set(target_pages)
    selected = []
    for chunk in chunks:
        chunk_pages = set(pages_from_chunk(chunk))
        if chunk_pages & target_pages:
            selected.append(chunk)
    return selected


def mapping_rows_for_pages(mapping_rows, target_pages):
    target_pages = set(target_pages)
    selected = []
    for row in mapping_rows:
        row_pages = set(parse_pages(row.get("pages", [])))
        if row_pages & target_pages:
            selected.append(row)
    return selected


def linked_image_pages(mapping_rows):
    pages = set()
    for row in mapping_rows:
        row_pages = set(parse_pages(row.get("pages", [])))
        for image_path in row.get("linked_images", []):
            page = image_page_from_name(image_path)
            if page:
                pages.add(page)
        for candidate in row.get("top_candidates", [])[:3]:
            page = candidate.get("page")
            if str(page).isdigit() and any(abs(int(page) - row_page) <= IMAGE_PAGE_RADIUS for row_page in row_pages):
                pages.add(int(page))
    return pages


def stage_records(questions):
    grouped = defaultdict(list)
    for row in questions:
        grouped[row["실습 단계"]].append(row)
    return grouped


def make_context_rows():
    questions = read_csv_dicts(QUESTION_SET_PATH)
    chunks = load_json(TEXT_CHUNKS_PATH)
    mapping_report = load_json(TEXT_IMAGE_MAPPING_REPORT_PATH)

    rows = []
    for index, (stage, records) in enumerate(sorted(stage_records(questions).items()), start=1):
        question_pages = sorted({page for row in records for page in parse_pages(row["페이지"])})
        text_pages = expand_pages(question_pages, TEXT_PAGE_RADIUS)
        image_pages = expand_pages(question_pages, IMAGE_PAGE_RADIUS)

        related_chunks = chunks_for_pages(chunks, text_pages)
        related_mapping_rows = mapping_rows_for_pages(mapping_report, text_pages)
        image_pages |= linked_image_pages(related_mapping_rows)

        headings = [
            normalize(chunk.get("heading"))
            for chunk in related_chunks
            if normalize(chunk.get("heading")) and normalize(chunk.get("heading")) != "문서 시작"
        ]
        unique_headings = []
        for heading in headings:
            if heading not in unique_headings:
                unique_headings.append(heading)

        question_texts = [row["질문"] for row in records]
        answer_texts = [row["정답 텍스트"] for row in records]
        chunk_texts = [chunk.get("text", "") for chunk in related_chunks[:8]]

        section_keywords = top_keywords([stage] + unique_headings, MAX_SECTION_KEYWORDS)
        content_keywords = top_keywords([stage] + question_texts + answer_texts + chunk_texts, MAX_CONTENT_KEYWORDS)
        action_keywords = top_keywords(question_texts, MAX_ACTION_KEYWORDS)

        qids = [row["질문 번호"] for row in records]
        evidence_headings = unique_headings[:3] or ["관련 섹션 제목 없음"]
        evidence = (
            f"{', '.join(qids)}의 정답 텍스트 페이지 {', '.join(map(str, question_pages))}와 "
            f"매뉴얼 섹션 {', '.join(evidence_headings)} 기준으로 구성"
        )

        rows.append(
            {
                "stage_id": f"S{index:03d}",
                "실습 단계": stage,
                "질문 수": str(len(records)),
                "근거 질문": ", ".join(qids),
                "텍스트 페이지 범위": compact_ranges(text_pages),
                "이미지 페이지 범위": compact_ranges(image_pages),
                "섹션 키워드": ", ".join(section_keywords),
                "본문 키워드": ", ".join(content_keywords),
                "동작/질문 키워드": ", ".join(action_keywords),
                "가중치": "1.00",
                "근거": evidence,
            }
        )

    return rows


def write_csv(rows):
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx():
    with OUTPUT_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.reader(f)]
    write_workbook(rows, OUTPUT_XLSX_PATH, "G4 단계 문맥 매핑표")


def write_markdown(rows):
    lines = [
        "# G4 단계 문맥 매핑표",
        "",
        "## 목적",
        "",
        "이 파일은 G4 상황 인지형 멀티모달 RAG에서 사용할 실습 단계별 문맥 매핑표를 요약한 문서입니다.",
        "정답 이미지 파일명을 직접 사용하지 않고, 실습 단계 라벨을 기준으로 관련 페이지 범위, 섹션 키워드, 본문 키워드를 구성했습니다.",
        "",
        "주의: 현재 매핑표는 1차 구현 검증을 위한 초안이며, 질의셋의 정답 텍스트 페이지를 근거로 포함합니다.",
        "논문 본 실험에서는 이 표를 매뉴얼 기준으로 사전 확정하고, 평가 결과를 본 뒤 수정하지 않는 방식으로 관리해야 합니다.",
        "",
        "## 생성 기준",
        "",
        "- 기준 질의셋: `SCIE용/data/03_question_set_70.csv`",
        "- 매뉴얼 텍스트 근거: `data/processed/text_chunks.json`",
        "- 텍스트-이미지 연결 근거: `data/processed/text_image_mapping_report.json`",
        "- 텍스트 페이지 범위: 정답 텍스트 페이지 기준 ±1 page",
        "- 이미지 페이지 범위: 정답 텍스트 페이지 기준 ±2 page + 해당 페이지 주변 텍스트-이미지 연결 후보 page",
        "",
        "## 매핑표 요약",
        "",
        "| 단계 ID | 실습 단계 | 질문 수 | 텍스트 페이지 범위 | 이미지 페이지 범위 | 대표 키워드 | 근거 질문 |",
        "|---|---|---:|---|---|---|---|",
    ]

    for row in rows:
        keywords = row["본문 키워드"].split(", ")[:5]
        lines.append(
            f"| {row['stage_id']} | {row['실습 단계']} | {row['질문 수']} | "
            f"{row['텍스트 페이지 범위']} | {row['이미지 페이지 범위']} | "
            f"{', '.join(keywords)} | {row['근거 질문']} |"
        )

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            "- `SCIE용/data/09_stage_context_map.csv`",
            "- `SCIE용/excel/09_stage_context_map.xlsx`",
        ]
    )

    OUTPUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = make_context_rows()
    write_csv(rows)
    write_xlsx()
    write_markdown(rows)
    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {OUTPUT_MD_PATH}")
    print(f"stages: {len(rows)}")


if __name__ == "__main__":
    main()
