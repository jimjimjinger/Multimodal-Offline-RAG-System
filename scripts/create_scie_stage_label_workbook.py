import csv
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCIE_DIR = next(path for path in PROJECT_ROOT.iterdir() if path.is_dir() and path.name.startswith("SCIE"))
SCIE_DATA_DIR = SCIE_DIR / "data"
SCIE_EXCEL_DIR = SCIE_DIR / "excel"
DEFAULT_CSV_PATH = SCIE_DATA_DIR / "01_question_stage_labels.csv"
DEFAULT_OUTPUT_PATH = SCIE_EXCEL_DIR / "01_question_stage_labels.xlsx"
DEFAULT_SHEET_NAME = "\uc2e4\uc2b5 \ub2e8\uacc4 \ub77c\ubca8"


def col_name(index):
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def cell_ref(row_idx, col_idx):
    return f"{col_name(col_idx)}{row_idx}"


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


def parse_drop_indexes(args):
    indexes = set()
    for arg in args:
        if not arg.startswith("--drop-index="):
            continue
        values = arg.split("=", 1)[1]
        for value in values.split(","):
            value = value.strip()
            if value.isdigit():
                indexes.add(int(value))
    return indexes


def read_rows(csv_path, drop_last=False, drop_indexes=None):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    if drop_last:
        rows = [row[:-1] for row in rows]
    if drop_indexes:
        rows = [
            [cell for idx, cell in enumerate(row, start=1) if idx not in drop_indexes]
            for row in rows
        ]
    return rows


def sheet_xml(rows):
    max_row = len(rows)
    max_col = max(len(row) for row in rows)
    dimension = f"A1:{cell_ref(max_row, max_col)}"
    widths = [11, 56, 48, 16, 30, 28, 18, 62]
    if len(widths) < max_col:
        widths.extend([24] * (max_col - len(widths)))

    cols = ["<cols>"]
    for idx, width in enumerate(widths, start=1):
        cols.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
    cols.append("</cols>")

    sheet_rows = ["<sheetData>"]
    for row_idx, values in enumerate(rows, start=1):
        if row_idx == 1:
            style_for_col = {col: 1 for col in range(1, max_col + 1)}
        else:
            style_for_col = {2: 2, 3: 2, 7: 2}
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


def styles_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="10"/><name val="Calibri"/></font>
    <font><b/><sz val="10"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>"""


def workbook_xml(sheet_name):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""


def workbook_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
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
</Types>"""


def write_workbook(rows, output_path, sheet_name):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("xl/workbook.xml", workbook_xml(sheet_name))
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        zf.writestr("xl/styles.xml", styles_xml())
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml(rows))


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT_PATH
    sheet_name = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SHEET_NAME
    drop_last = "--drop-last" in sys.argv[4:]
    drop_indexes = parse_drop_indexes(sys.argv[4:])
    rows = read_rows(csv_path, drop_last=drop_last, drop_indexes=drop_indexes)
    write_workbook(rows, output_path, sheet_name)
    print(f"created: {output_path}")
    print(f"rows: {len(rows) - 1}")


if __name__ == "__main__":
    main()
