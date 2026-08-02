import csv
import sys
from collections import Counter
from pathlib import Path

from sentence_transformers import SentenceTransformer


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
    configure_model_cache,
)
from stage_classifier import (  # noqa: E402
    DEFAULT_STAGE_MIN_MARGIN,
    DEFAULT_STAGE_MIN_SCORE,
    build_stage_profiles,
    classify_stage,
    encode_stage_profiles,
)


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
OUTPUT_CSV_PATH = SCIE_DATA_DIR / "29_stage_classifier_eval.csv"
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "29_stage_classifier_eval.xlsx"
REPORT_PATH = SCIE_DIR / "29_stage_classifier_results.md"

FIELDS = [
    "질문 번호",
    "질문",
    "정답 실습 단계",
    "예측 실습 단계",
    "G4 적용 단계",
    "최고 점수",
    "1-2위 점수 차이",
    "Top-1 정답",
    "Top-3 정답",
    "Top-5 정답",
    "G4 적용",
    "Top-5 후보",
]


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows):
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(rows):
    table = [FIELDS] + [[row.get(field, "") for field in FIELDS] for row in rows]
    write_workbook(table, OUTPUT_XLSX_PATH, "단계 추정 평가")


def yes_no(value):
    return "O" if value else "X"


def candidate_text(candidates):
    return " | ".join(
        f"{rank}. {item['stage']} ({item['score']:.3f})"
        for rank, item in enumerate(candidates, start=1)
    )


def percent(value):
    return f"{value * 100:.1f}%"


def summarize(rows):
    total = len(rows)
    top1 = sum(1 for row in rows if row["Top-1 정답"] == "O")
    top3 = sum(1 for row in rows if row["Top-3 정답"] == "O")
    top5 = sum(1 for row in rows if row["Top-5 정답"] == "O")
    passed = sum(1 for row in rows if row["G4 적용"] == "O")
    top1_when_passed = sum(
        1 for row in rows if row["G4 적용"] == "O" and row["Top-1 정답"] == "O"
    )
    scores = [float(row["최고 점수"]) for row in rows]
    return {
        "total": total,
        "top1": top1,
        "top3": top3,
        "top5": top5,
        "passed": passed,
        "top1_when_passed": top1_when_passed,
        "avg_score": sum(scores) / total if total else 0.0,
    }


def write_report(rows, summary):
    errors = [row for row in rows if row["Top-1 정답"] == "X"]
    low_confidence = [row for row in rows if row["G4 적용"] == "X"]
    stage_counts = Counter(row["정답 실습 단계"] for row in rows)
    lines = [
        "# 실습 단계 추정 평가 결과",
        "",
        "## 평가 개요",
        "",
        "G4 구현을 위해 질문과 실습 단계 context profile 간 BGE-M3 의미 유사도를 비교하여 실습 단계를 추정하였다.",
        "실습 단계 context profile은 `11_stage_context_map_manual`의 실습 단계명, section keyword, 본문 keyword, 동작/질문 keyword, 근거 문장으로 구성하였다.",
        "",
        "## 전체 결과",
        "",
        "| 지표 | 결과 |",
        "|---|---:|",
        f"| 전체 질문 수 | {summary['total']} |",
        f"| Top-1 stage accuracy | {percent(summary['top1'] / summary['total'])} ({summary['top1']}/{summary['total']}) |",
        f"| Top-3 stage accuracy | {percent(summary['top3'] / summary['total'])} ({summary['top3']}/{summary['total']}) |",
        f"| Top-5 stage accuracy | {percent(summary['top5'] / summary['total'])} ({summary['top5']}/{summary['total']}) |",
        f"| G4 적용률 | {percent(summary['passed'] / summary['total'])} ({summary['passed']}/{summary['total']}) |",
        f"| G4 적용 시 Top-1 accuracy | {percent(summary['top1_when_passed'] / summary['passed']) if summary['passed'] else '0.0%'} ({summary['top1_when_passed']}/{summary['passed']}) |",
        f"| 평균 최고 점수 | {summary['avg_score']:.3f} |",
        f"| 적용 기준 점수 | {DEFAULT_STAGE_MIN_SCORE:.2f} |",
        f"| 적용 최소 margin | {DEFAULT_STAGE_MIN_MARGIN:.2f} |",
        "",
        "## 해석",
        "",
        "- Top-1 accuracy는 단계 추정 기반 G4에 바로 사용할 수 있는 단계 예측 정확도이다.",
        "- Top-3 accuracy가 높으면 앱에서 단계 추정 후보를 보여주고 사용자가 선택하는 보조 방식에 적합하다.",
        "- 기준점수 미만이거나 1위와 2위의 점수 차이가 작아 애매한 질문은 G4를 적용하지 않고 G3로 처리하는 것이 안전하다.",
        "",
        "## Top-1 오분류 사례",
        "",
        "| 질문 번호 | 정답 단계 | 예측 단계 | 점수 | Top-5 후보 |",
        "|---|---|---|---:|---|",
    ]

    for row in errors[:20]:
        lines.append(
            f"| {row['질문 번호']} | {row['정답 실습 단계']} | {row['예측 실습 단계']} | "
            f"{float(row['최고 점수']):.3f} | {row['Top-5 후보']} |"
        )

    lines.extend(
        [
            "",
            "## 낮은 신뢰도 사례",
            "",
            "| 질문 번호 | 정답 단계 | 예측 단계 | 점수 |",
            "|---|---|---|---:|",
        ]
    )
    for row in low_confidence[:20]:
        lines.append(
            f"| {row['질문 번호']} | {row['정답 실습 단계']} | {row['예측 실습 단계']} | "
            f"{float(row['최고 점수']):.3f} |"
        )

    lines.extend(
        [
            "",
            "## 단계 라벨 분포",
            "",
            "| 실습 단계 | 질문 수 |",
            "|---|---:|",
        ]
    )
    for stage, count in sorted(stage_counts.items()):
        lines.append(f"| {stage} | {count} |")

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            f"- `{OUTPUT_CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{OUTPUT_XLSX_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_model_cache()
    embedder = SentenceTransformer("BAAI/bge-m3")
    profiles = build_stage_profiles(STAGE_CONTEXT_MAP_MANUAL_PATH)
    profile_embeddings = encode_stage_profiles(embedder, profiles)

    rows = []
    for question in read_questions():
        result = classify_stage(
            question=question["질문"],
            embedder=embedder,
            profiles=profiles,
            profile_embeddings=profile_embeddings,
            top_k=5,
        )
        expected_stage = question["실습 단계"]
        top_candidates = result["top_candidates"]
        candidate_stages = [item["stage"] for item in top_candidates]
        predicted_stage = result["predicted_stage"]
        rows.append(
            {
                "질문 번호": question["질문 번호"],
                "질문": question["질문"],
                "정답 실습 단계": expected_stage,
                "예측 실습 단계": predicted_stage,
                "G4 적용 단계": result["stage_label"] or "",
                "최고 점수": f"{result['score']:.4f}",
                "1-2위 점수 차이": f"{result['margin']:.4f}",
                "Top-1 정답": yes_no(predicted_stage == expected_stage),
                "Top-3 정답": yes_no(expected_stage in candidate_stages[:3]),
                "Top-5 정답": yes_no(expected_stage in candidate_stages[:5]),
                "G4 적용": yes_no(result["used"]),
                "Top-5 후보": candidate_text(top_candidates),
            }
        )

    write_csv(rows)
    write_xlsx(rows)
    summary = summarize(rows)
    write_report(rows, summary)

    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {REPORT_PATH}")
    print(f"Top-1: {summary['top1']}/{summary['total']} ({percent(summary['top1'] / summary['total'])})")
    print(f"Top-3: {summary['top3']}/{summary['total']} ({percent(summary['top3'] / summary['total'])})")
    print(f"Top-5: {summary['top5']}/{summary['total']} ({percent(summary['top5'] / summary['total'])})")


if __name__ == "__main__":
    main()
