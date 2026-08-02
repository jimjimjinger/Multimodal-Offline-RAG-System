import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import EVALUATION_DATA_DIR  # noqa: E402


RAW_EVAL_PATH = EVALUATION_DATA_DIR / "model_eval_raw.csv"
TESTSET_PATH = EVALUATION_DATA_DIR / "testset.xlsx"
OUTPUT_PATH = EVALUATION_DATA_DIR / "manual_eval_by_model.xlsx"

HEADERS = [
    "\uc9c8\ubb38 \ubc88\ud638",
    "\uc9c8\ubb38",
    "\uc815\ub2f5 \ud14d\uc2a4\ud2b8",
    "\ubaa8\ub378 \ud14d\uc2a4\ud2b8 \ub2f5\ubcc0",
    "\uc815\ub2f5 \uc774\ubbf8\uc9c0",
    "\ubaa8\ub378 \uc774\ubbf8\uc9c0 \ub2f5\ubcc0",
    "\ud14d\uc2a4\ud2b8 \ud3c9\uac00",
    "\uc774\ubbf8\uc9c0 \ud3c9\uac00",
]
MODEL_SHEETS = [
    ("qwen", "Qwen"),
    ("gemma", "Gemma"),
    ("llama", "Llama"),
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
        ref = cell_ref(row_idx, col_idx)
        cells.append(string_cell(ref, value, style_for_col.get(col_idx, 0)))
    return f'<row r="{row_idx}">{"".join(cells)}</row>'


def parse_images(value, limit=10):
    try:
        images = json.loads(value or "[]")
    except json.JSONDecodeError:
        images = []
    if not isinstance(images, list):
        return ""

    names = []
    for rank, image in enumerate(images[:limit], start=1):
        name = image.get("name", "")
        if name:
            names.append(f"{rank}. {name}")
    return "\n".join(names)


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

    records = {}
    for row in rows[1:]:
        row = row + [""] * (5 - len(row))
        records[row[0]] = {
            "qid": row[0],
            "question": row[1],
            "expected_answer": row[2],
            "expected_page": row[3],
            "expected_image": row[4],
        }
    return records


def load_rows_by_model():
    testset = read_testset()
    rows_by_model = {model_key: [] for model_key, _ in MODEL_SHEETS}

    if RAW_EVAL_PATH.exists():
        with RAW_EVAL_PATH.open("r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                model_key = row.get("model_key", "")
                if model_key not in rows_by_model:
                    continue

                qid = row.get("qid", "")
                truth = testset.get(qid, {})
                rows_by_model[model_key].append(
                    [
                        qid,
                        truth.get("question") or row.get("question", ""),
                        truth.get("expected_answer") or row.get("expected_answer", ""),
                        row.get("answer", ""),
                        truth.get("expected_image") or row.get("expected_image", ""),
                        parse_images(row.get("retrieved_images", "")),
                        "",
                        "",
                    ]
                )
    else:
        for model_key in rows_by_model:
            for qid, truth in testset.items():
                rows_by_model[model_key].append(
                    [
                        qid,
                        truth.get("question", ""),
                        truth.get("expected_answer", ""),
                        "",
                        truth.get("expected_image", ""),
                        "",
                        "",
                        "",
                    ]
                )

    for model_key in rows_by_model:
        rows_by_model[model_key].sort(key=lambda row: question_number(row[0]))
    return rows_by_model


def sheet_xml(rows):
    all_rows = [HEADERS] + rows
    max_row = len(all_rows)
    dimension = f"A1:H{max_row}"
    widths = [12, 46, 46, 68, 28, 44, 14, 14]

    cols = ["<cols>"]
    for idx, width in enumerate(widths, start=1):
        cols.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
    cols.append("</cols>")

    sheet_rows = ["<sheetData>"]
    for row_idx, values in enumerate(all_rows, start=1):
        if row_idx == 1:
            style_for_col = {col: 1 for col in range(1, 9)}
        else:
            style_for_col = {2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3}
        sheet_rows.append(row_xml(row_idx, values, style_for_col))
    sheet_rows.append("</sheetData>")

    validations = (
        '<dataValidations count="2">'
        f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="G2:G{max_row}">'
        '<formula1>"O,\u25b3,X"</formula1>'
        "</dataValidation>"
        f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="H2:H{max_row}">'
        '<formula1>"O,\u25b3,X"</formula1>'
        "</dataValidation>"
        "</dataValidations>"
    )

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
        f"{validations}"
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


def workbook_xml():
    sheets = []
    for idx, (_, sheet_name) in enumerate(MODEL_SHEETS, start=1):
        sheets.append(f'<sheet name="{sheet_name}" sheetId="{idx}" r:id="rId{idx}"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheets)}</sheets>'
        "</workbook>"
    )


def workbook_rels_xml():
    rels = []
    for idx, _ in enumerate(MODEL_SHEETS, start=1):
        rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{len(MODEL_SHEETS) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}'
        "</Relationships>"
    )


def root_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def content_types_xml():
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx, _ in enumerate(MODEL_SHEETS, start=1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}'
        "</Types>"
    )


def write_workbook(rows_by_model, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        zf.writestr("xl/styles.xml", styles_xml())
        for idx, (model_key, _) in enumerate(MODEL_SHEETS, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml(rows_by_model[model_key]))


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    rows_by_model = load_rows_by_model()
    write_workbook(rows_by_model, output_path)
    total_rows = sum(len(rows) for rows in rows_by_model.values())
    print(f"created: {output_path}")
    print(f"rows: {total_rows}")


if __name__ == "__main__":
    main()
