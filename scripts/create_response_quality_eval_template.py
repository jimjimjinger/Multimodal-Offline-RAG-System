import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import SCIE_DATA_DIR, SCIE_EXCEL_DIR  # noqa: E402


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
OUTPUT_CSV_PATH = SCIE_DATA_DIR / "17_response_quality_eval_template.csv"
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "17_response_quality_eval_template.xlsx"


GROUPS = [
    ("G2", "텍스트 기반 RAG"),
    ("G3", "멀티모달 RAG"),
    ("G4", "상황 인지형 멀티모달 RAG"),
]

MODELS = [
    ("Qwen", "qwen2.5:7b"),
    ("Gemma", "gemma2:9b"),
    ("Llama", "llama3.1:8b"),
]

FIELDS = [
    "질문 번호",
    "비교군",
    "비교군 설명",
    "모델",
    "모델 ID",
    "질문",
    "실습 단계",
    "질문 유형",
    "정답 텍스트",
    "정답 이미지",
    "검색 텍스트 순위",
    "검색 이미지 순위",
    "모델 답변",
    "정확성(1-5)",
    "구체성(1-5)",
    "실습 단계 적합성(1-5)",
    "안전성(1-5)",
    "이해 용이성(1-5)",
    "평균 점수",
    "최종 판정(O/△/X)",
    "평가 메모",
]


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def make_rows():
    rows = []
    for question in read_questions():
        for group_id, group_label in GROUPS:
            for model_name, model_id in MODELS:
                rows.append(
                    {
                        "질문 번호": question["질문 번호"],
                        "비교군": group_id,
                        "비교군 설명": group_label,
                        "모델": model_name,
                        "모델 ID": model_id,
                        "질문": question["질문"],
                        "실습 단계": question["실습 단계"],
                        "질문 유형": question["질문 유형"],
                        "정답 텍스트": question["정답 텍스트"],
                        "정답 이미지": question["정답 이미지"],
                        "검색 텍스트 순위": "",
                        "검색 이미지 순위": "" if group_id == "G2" else "",
                        "모델 답변": "",
                        "정확성(1-5)": "",
                        "구체성(1-5)": "",
                        "실습 단계 적합성(1-5)": "",
                        "안전성(1-5)": "",
                        "이해 용이성(1-5)": "",
                        "평균 점수": "",
                        "최종 판정(O/△/X)": "",
                        "평가 메모": "",
                    }
                )
    return rows


def write_csv(rows):
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(rows):
    table = [FIELDS] + [[row.get(field, "") for field in FIELDS] for row in rows]
    write_workbook(table, OUTPUT_XLSX_PATH, "응답 품질 평가")


def main():
    rows = make_rows()
    write_csv(rows)
    write_xlsx(rows)
    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
