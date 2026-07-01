import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import EVALUATION_DATA_DIR  # noqa: E402


RAW_EVAL_PATH = EVALUATION_DATA_DIR / "model_eval_raw.csv"
TESTSET_PATH = EVALUATION_DATA_DIR / "testset.xlsx"
OUTPUT_PATH = EVALUATION_DATA_DIR / "image_eval.xlsx"

IMAGE_O_LIMIT = 5
IMAGE_PARTIAL_LIMIT = 10
PARTIAL = "\u25b3"

HEADERS = [
    "\uc9c8\ubb38 \ubc88\ud638",
    "\uc9c8\ubb38",
    "\uc815\ub2f5 \uc774\ubbf8\uc9c0",
    "\uac80\uc0c9 \uc774\ubbf8\uc9c0 Top-10",
    "\uc815\ub2f5 \uc21c\uc704",
    "\uc774\ubbf8\uc9c0 \ud3c9\uac00",
]


def col_name(index):
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def cell_ref(row_idx, col_idx):
    return f"{col_name(col_idx)}{row_idx}"


def col_to_idx(cell_ref_value):
    letters = "".join(ch for ch in cell_ref_value if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + ord(ch.upper()) - ord("A") + 1
    return idx - 1


def xml_escape(value):
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def string_cell(ref, value, style=0):
    if value in (None, ""):
        return f'<c r="{ref}" s="{style}"/>'
    text = xml_escape(value)
    preserve = ' xml:space="preserve"' if str(value).strip() != str(value) or "\n" in str(value) else ""
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t{preserve}>{text}</t></is></c>'


def row_xml(row_idx, values, style_for_col=None):
    style_for_col = style_for_col or {}
    cells = []
    for col_idx, value in enumerate(values, start=1):
        cells.append(string_cell(cell_ref(row_idx, col_idx), value, style_for_col.get(col_idx, 0)))
    return f'<row r="{row_idx}">{"".join(cells)}</row>'


def question_number(qid):
    return int("".join(ch for ch in str(qid) if ch.isdigit()) or 0)


def read_testset():
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(TESTSET_PATH) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))

        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                idx = col_to_idx(cell.attrib.get("r", "A1"))
                while len(values) <= idx:
                    values.append("")
                value_node = cell.find("a:v", ns)
                value = "" if value_node is None else value_node.text or ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[idx] = value
            rows.append(values)

    records = []
    for row in rows[1:]:
        row = row + [""] * (5 - len(row))
        records.append(
            {
                "qid": row[0],
                "question": row[1],
                "expected_image": row[4],
            }
        )
    return sorted(records, key=lambda row: question_number(row["qid"]))


def read_retrieved_images():
    by_qid = {}
    if not RAW_EVAL_PATH.exists():
        return by_qid

    with RAW_EVAL_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            qid = row.get("qid", "")
            if qid in by_qid:
                continue
            try:
                images = json.loads(row.get("retrieved_images") or "[]")
            except json.JSONDecodeError:
                images = []
            if not isinstance(images, list):
                images = []
            by_qid[qid] = [image.get("name", "") for image in images[:IMAGE_PARTIAL_LIMIT] if image.get("name")]
    return by_qid


def grade_image(expected_image, retrieved_names):
    for rank, name in enumerate(retrieved_names[:IMAGE_PARTIAL_LIMIT], start=1):
        if name == expected_image:
            return rank, "O" if rank <= IMAGE_O_LIMIT else PARTIAL
    return "", "X"


def build_rows():
    retrieved_by_qid = read_retrieved_images()
    rows = []
    for record in read_testset():
        names = retrieved_by_qid.get(record["qid"], [])
        rank, grade = grade_image(record["expected_image"], names)
        rows.append(
            [
                record["qid"],
                record["question"],
                record["expected_image"],
                "\n".join(f"{idx}. {name}" for idx, name in enumerate(names, start=1)),
                rank,
                grade,
            ]
        )
    return rows


def sheet_xml(rows):
    all_rows = [HEADERS] + rows
    max_row = len(all_rows)
    dimension = f"A1:F{max_row}"
    widths = [12, 52, 30, 48, 14, 14]

    cols = ["<cols>"]
    for idx, width in enumerate(widths, start=1):
        cols.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
    cols.append("</cols>")

    sheet_rows = ["<sheetData>"]
    for row_idx, values in enumerate(all_rows, start=1):
        if row_idx == 1:
            style_for_col = {col: 1 for col in range(1, 7)}
        else:
            style_for_col = {2: 2, 3: 2, 4: 2, 5: 3, 6: 3}
        sheet_rows.append(row_xml(row_idx, values, style_for_col))
    sheet_rows.append("</sheetData>")

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'{"".join(cols)}'
        f'{"".join(sheet_rows)}'
        f'<autoFilter ref="{dimension}"/>'
        "</worksheet>"
    )


def summary_xml(rows):
    counts = Counter(row[5] for row in rows)
    summary_rows = [
        ["\uc774\ubbf8\uc9c0 \ud3c9\uac00", "\uac1c\uc218"],
        ["O", counts["O"]],
        [PARTIAL, counts[PARTIAL]],
        ["X", counts["X"]],
        ["Total", len(rows)],
    ]
    sheet_rows = ["<sheetData>"]
    for row_idx, values in enumerate(summary_rows, start=1):
        style = {1: 1, 2: 1} if row_idx == 1 else {1: 3, 2: 3}
        sheet_rows.append(row_xml(row_idx, values, style))
    sheet_rows.append("</sheetData>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:B5"/>'
        '<cols><col min="1" max="1" width="18" customWidth="1"/>'
        '<col min="2" max="2" width="12" customWidth="1"/></cols>'
        f'{"".join(sheet_rows)}'
        "</worksheet>"
    )


def styles_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="10"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>"""


def write_workbook(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        zf.writestr("xl/styles.xml", styles_xml())
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml(rows))
        zf.writestr("xl/worksheets/sheet2.xml", summary_xml(rows))


def workbook_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Image Eval" sheetId="1" r:id="rId1"/>
    <sheet name="Summary" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""


def workbook_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def root_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def content_types_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    rows = build_rows()
    write_workbook(rows, output_path)
    counts = Counter(row[5] for row in rows)
    print(f"created: {output_path}")
    print(f"O={counts['O']} {PARTIAL}={counts[PARTIAL]} X={counts['X']} total={len(rows)}")


if __name__ == "__main__":
    main()
