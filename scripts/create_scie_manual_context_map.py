import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import (  # noqa: E402
    SCIE_DATA_DIR,
    SCIE_DIR,
    SCIE_EXCEL_DIR,
    STAGE_CONTEXT_MAP_MANUAL_PATH,
    TEXT_CHUNKS_PATH,
    TEXT_IMAGE_MAPPING_REPORT_PATH,
)


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
OUTPUT_CSV_PATH = STAGE_CONTEXT_MAP_MANUAL_PATH
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "11_stage_context_map_manual.xlsx"
OUTPUT_MD_PATH = SCIE_DIR / "11_stage_context_map_manual.md"

TEXT_PAGE_RADIUS = 1
IMAGE_PAGE_RADIUS = 2
TOP_CHUNKS_PER_STAGE = 5


STOPWORDS = {
    "관련",
    "단계",
    "설정",
    "확인",
    "연결",
    "사용",
    "조작",
    "관리",
    "시스템",
    "로봇",
    "제어기",
    "컨트롤러",
    "화면",
    "메뉴",
    "기능",
    "모듈",
}

TERM_EXPANSIONS = {
    "안전": ["safety", "safe", "stop", "안전"],
    "전원": ["power", "전원"],
    "접지": ["ground", "earth", "접지"],
    "극성": ["polarity", "극성", "전압"],
    "케이블": ["cable", "connector", "케이블", "커넥터"],
    "방수": ["waterproof", "grommet", "방수", "그로밋"],
    "설치": ["installation", "install", "mount", "설치"],
    "기구": ["mechanical", "base", "bolt", "torque", "고정"],
    "고정": ["fix", "bolt", "torque", "mounting", "고정"],
    "운반": ["transport", "carry", "packaging", "운반"],
    "마운팅": ["mount", "mounting", "ceiling", "벽면", "천장"],
    "매니퓰레이터": ["manipulator", "robot cable", "매니퓰레이터"],
    "티치": ["teach", "pendant", "tp", "티치", "펜던트"],
    "펜던트": ["teach pendant", "pendant", "emergency", "usb", "power"],
    "비상정지": ["emergency stop", "emergency", "stop", "em", "비상정지"],
    "비상": ["emergency", "stop", "비상"],
    "backdrive": ["backdrive", "brake", "브레이크"],
    "recovery": ["recovery", "packaging", "복구"],
    "패키징": ["packaging", "package", "패키징"],
    "i/o": ["i/o", "io", "digital", "input", "output", "tb", "gnd", "vcc"],
    "io": ["i/o", "io", "digital", "input", "output", "tb", "gnd", "vcc"],
    "입력": ["input", "di", "si", "입력"],
    "출력": ["output", "do", "출력"],
    "디지털": ["digital", "input", "output", "디지털"],
    "아날로그": ["analog", "voltage", "current", "아날로그"],
    "엔코더": ["encoder", "a phase", "b phase", "z phase", "엔코더"],
    "안전설정": ["safety settings", "safety setting", "zone", "parameter"],
    "구역": ["zone", "space", "safety settings", "구역"],
    "zone": ["zone", "space", "shape", "safety settings"],
    "공간": ["space", "zone", "point", "height"],
    "충돌": ["collision", "sensitivity", "충돌"],
    "협착": ["crushing", "prevention", "협착"],
    "remote": ["remote control", "remote", "control"],
    "원격": ["remote control", "remote", "control"],
    "네트워크": ["network", "wan", "lan", "ethernet", "tcp/ip", "modbus"],
    "profinet": ["profinet", "slot", "robot state"],
    "tcp": ["tcp", "tool center point", "tool coordinate", "offset"],
    "좌표": ["coordinate", "coordinates", "axis", "x", "y", "z"],
    "툴": ["tool", "flange", "tool settings", "tool shape", "tool weight"],
    "플랜지": ["flange", "tool flange", "x1", "pin", "rs-485"],
    "직접교시": ["direct teaching", "cockpit", "teaching"],
    "cockpit": ["cockpit", "direct teaching", "button"],
    "jog": ["jog", "task motion", "joint motion", "manual"],
    "프로그래밍": ["programming", "task editor", "command", "program"],
    "모션": ["motion", "movej", "movel", "linear", "joint"],
    "task": ["task editor", "task", "program", "command"],
    "editor": ["task editor", "program", "command"],
    "home": ["home position", "home"],
    "force": ["force", "external force", "custom code"],
    "힘": ["force", "external force", "custom code"],
    "로그": ["log", "logs", "error log"],
    "업데이트": ["update", "software", "package", ".dm"],
    "초기화": ["factory reset", "reset", "database", "log"],
    "사용자": ["user", "account", "password", "supervisor"],
    "권한": ["user", "account", "password", "supervisor"],
    "dart": ["dart-platform", "dart", "robot settings", "platform"],
    "robot": ["robot settings", "robot"],
    "settings": ["settings", "robot settings", "parameter"],
}


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def tokenize(value):
    tokens = []
    for token in re.findall(r"[0-9A-Za-z가-힣]+", normalize(value).lower()):
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def stage_terms(stage):
    normalized = stage.lower().replace("/", " ").replace("-", " ")
    base_terms = tokenize(normalized)
    phrase_terms = [part.strip().lower() for part in re.split(r"[/|-]", stage) if part.strip()]
    terms = []
    for term in phrase_terms + base_terms:
        if term and term not in terms:
            terms.append(term)
        compact = term.replace(" ", "")
        if compact in TERM_EXPANSIONS:
            for expansion in TERM_EXPANSIONS[compact]:
                if expansion not in terms:
                    terms.append(expansion)
        if term in TERM_EXPANSIONS:
            for expansion in TERM_EXPANSIONS[term]:
                if expansion not in terms:
                    terms.append(expansion)
    return terms


def parse_pages(value):
    if isinstance(value, list):
        return [int(page) for page in value if str(page).isdigit()]
    return [int(match) for match in re.findall(r"\d+", str(value or ""))]


def image_page_from_name(value):
    match = re.search(r"page_(\d+)_", str(value or ""))
    return int(match.group(1)) if match else None


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


def score_chunk(chunk, terms):
    heading = normalize(chunk.get("heading")).lower()
    text = normalize(chunk.get("text")).lower()
    score = 0.0
    matched = []

    for term in terms:
        term = term.lower()
        if not term:
            continue
        if term in heading:
            score += 4.0
            matched.append(term)
        if term in text:
            score += 1.0
            matched.append(term)

    pages = parse_pages(chunk.get("pages"))
    if pages and min(pages) <= 20:
        score *= 0.7
    return score, list(dict.fromkeys(matched))


def select_chunks(stage, chunks):
    terms = stage_terms(stage)
    scored = []
    for chunk in chunks:
        score, matched = score_chunk(chunk, terms)
        if score <= 0:
            continue
        scored.append((score, len(matched), chunk, matched))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[:TOP_CHUNKS_PER_STAGE], terms


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


def mapping_rows_by_page(mapping_report):
    by_page = {}
    for row in mapping_report:
        for page in parse_pages(row.get("pages")):
            by_page.setdefault(page, []).append(row)
    return by_page


def linked_image_pages_for_text_pages(text_pages, mapping_by_page):
    pages = set()
    for text_page in text_pages:
        for row in mapping_by_page.get(text_page, []):
            for image_path in row.get("linked_images", []):
                image_page = image_page_from_name(image_path)
                if image_page and abs(image_page - text_page) <= IMAGE_PAGE_RADIUS:
                    pages.add(image_page)
    return pages


def write_csv(rows):
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(rows):
    table = [list(rows[0].keys())]
    for row in rows:
        table.append([row.get(field, "") for field in table[0]])
    write_workbook(table, OUTPUT_XLSX_PATH, "G4 수동 확정 매핑표")


def write_markdown(rows):
    lines = [
        "# G4 매뉴얼 기준 단계 문맥 매핑표",
        "",
        "## 목적",
        "",
        "이 문서는 논문 실험에서 사용할 수 있도록 정답 페이지/정답 이미지/정답 텍스트를 사용하지 않고 만든 G4 단계 문맥 매핑표입니다.",
        "실습 단계 라벨과 매뉴얼에서 추출된 section heading 및 본문 텍스트만 이용해 관련 페이지 범위와 키워드를 산정했습니다.",
        "",
        "## 생성 기준",
        "",
        "- 사용한 정보: 실습 단계명, 매뉴얼 텍스트 chunk, 텍스트-이미지 연결 정보",
        "- 사용하지 않은 정보: 질문별 정답 텍스트, 정답 페이지, 정답 이미지 파일명",
        "- 텍스트 페이지 범위: 단계명과 매뉴얼 chunk 간 키워드 매칭 상위 chunk 기준 ±1 page",
        "- 이미지 페이지 범위: 텍스트 페이지 범위 기준 ±2 page + 해당 매뉴얼 chunk에 연결된 주변 이미지 page",
        "",
        "## 매핑표 요약",
        "",
        "| 단계 ID | 실습 단계 | 텍스트 페이지 범위 | 이미지 페이지 범위 | 대표 키워드 | 근거 |",
        "|---|---|---|---|---|---|",
    ]

    for row in rows:
        keywords = row["본문 키워드"].split(", ")[:5]
        lines.append(
            f"| {row['stage_id']} | {row['실습 단계']} | {row['텍스트 페이지 범위']} | "
            f"{row['이미지 페이지 범위']} | {', '.join(keywords)} | {row['근거']} |"
        )

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            "- `SCIE용/data/11_stage_context_map_manual.csv`",
            "- `SCIE용/excel/11_stage_context_map_manual.xlsx`",
        ]
    )
    OUTPUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_rows():
    questions = read_csv_dicts(QUESTION_SET_PATH)
    chunks = load_json(TEXT_CHUNKS_PATH)
    mapping_report = load_json(TEXT_IMAGE_MAPPING_REPORT_PATH)
    mapping_by_page = mapping_rows_by_page(mapping_report)

    stages = sorted({row["실습 단계"] for row in questions})
    rows = []
    for index, stage in enumerate(stages, start=1):
        selected, terms = select_chunks(stage, chunks)
        selected_chunks = [item[2] for item in selected]
        selected_pages = sorted({page for chunk in selected_chunks for page in parse_pages(chunk.get("pages"))})
        if not selected_pages:
            selected_pages = []

        text_pages = expand_pages(selected_pages, TEXT_PAGE_RADIUS)
        image_pages = expand_pages(selected_pages, IMAGE_PAGE_RADIUS)
        image_pages |= linked_image_pages_for_text_pages(text_pages, mapping_by_page)

        headings = [normalize(chunk.get("heading")) for chunk in selected_chunks if normalize(chunk.get("heading"))]
        chunk_texts = [chunk.get("text", "") for chunk in selected_chunks]
        matched_terms = []
        for _, _, _, matched in selected:
            matched_terms.extend(matched)

        section_keywords = top_keywords([stage] + headings + terms, 8)
        content_keywords = top_keywords([stage] + terms + chunk_texts, 14)
        action_keywords = top_keywords([stage] + terms, 10)

        evidence_parts = []
        for score, _, chunk, matched in selected[:3]:
            pages = compact_ranges(parse_pages(chunk.get("pages")))
            heading = normalize(chunk.get("heading")) or "섹션 제목 없음"
            evidence_parts.append(f"{heading} p.{pages} match={','.join(matched[:4])} score={score:.1f}")
        evidence = " | ".join(evidence_parts) if evidence_parts else "단계명과 일치하는 매뉴얼 chunk 없음"

        rows.append(
            {
                "stage_id": f"M{index:03d}",
                "실습 단계": stage,
                "질문 수": str(sum(1 for row in questions if row["실습 단계"] == stage)),
                "근거 질문": "평가 정답 미사용",
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


def main():
    rows = make_rows()
    write_csv(rows)
    write_xlsx(rows)
    write_markdown(rows)
    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {OUTPUT_MD_PATH}")
    print(f"stages: {len(rows)}")


if __name__ == "__main__":
    main()
