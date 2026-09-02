import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCIE_DIR = PROJECT_ROOT / "SCIE용"
DATA_DIR = SCIE_DIR / "data"
MANUSCRIPT_SOURCE = SCIE_DIR / "논문" / "IEEE Access 영문 통합 원고.md"

FINAL_DETAIL = DATA_DIR / "15_g1_g2_g3_g4_retrieval_results.csv"
FINAL_SUMMARY = DATA_DIR / "15_g1_g2_g3_g4_summary.csv"
ABLATION_DETAIL = DATA_DIR / "32_bbox_siglip_ablation_details.csv"
ABLATION_SUMMARY = DATA_DIR / "32_bbox_siglip_ablation_summary.csv"
BOOTSTRAP_RESULTS = DATA_DIR / "31_g3_g4_paired_bootstrap_ci.csv"


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_rank(value):
    value = str(value or "").strip()
    return int(value) if value.isdigit() else None


def metrics(rows, column):
    ranks = [parse_rank(row[column]) for row in rows]
    total = len(ranks)
    return {
        "Image Recall@1": f"{100 * sum(rank == 1 for rank in ranks) / total:.1f}%",
        "Image Recall@5": f"{100 * sum(rank is not None and rank <= 5 for rank in ranks) / total:.1f}%",
        "Image Recall@10": f"{100 * sum(rank is not None and rank <= 10 for rank in ranks) / total:.1f}%",
        "Image MRR": f"{sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / total:.3f}",
    }


def assert_metrics(actual, expected, label):
    for metric, value in actual.items():
        if expected[metric] != value:
            raise AssertionError(f"{label} {metric}: calculated={value}, saved={expected[metric]}")


def main():
    final_detail = read_rows(FINAL_DETAIL)
    if len(final_detail) != 70:
        raise AssertionError(f"최종 검색 상세 행 수가 70이 아닙니다: {len(final_detail)}")

    final_summary = {row["비교군"]: row for row in read_rows(FINAL_SUMMARY)}
    assert_metrics(metrics(final_detail, "G3 이미지 정답 순위"), final_summary["G3"], "G3")
    assert_metrics(metrics(final_detail, "G4 이미지 정답 순위"), final_summary["G4"], "G4")

    ablation_detail = read_rows(ABLATION_DETAIL)
    if len(ablation_detail) != 70:
        raise AssertionError(f"BBox/SigLIP 상세 행 수가 70이 아닙니다: {len(ablation_detail)}")
    ablation_summary = {row["configuration"]: row for row in read_rows(ABLATION_SUMMARY)}
    assert_metrics(
        metrics(ablation_detail, "BBox 기반 매핑 정답 순위"),
        ablation_summary["BBox-based mapping score"],
        "BBox mapping",
    )
    assert_metrics(
        metrics(ablation_detail, "BBox 필터 + SigLIP 정답 순위"),
        ablation_summary["BBox candidate filter + SigLIP ranking (final)"],
        "BBox filter + SigLIP",
    )

    bootstrap_rows = read_rows(BOOTSTRAP_RESULTS)
    if len(bootstrap_rows) != 4 or any(row["query_count"] != "70" for row in bootstrap_rows):
        raise AssertionError("paired bootstrap 결과는 70개 질의의 네 지표를 포함해야 합니다.")

    source = MANUSCRIPT_SOURCE.read_text(encoding="utf-8")
    for row in ablation_summary.values():
        expected_row = (
            f"| {row['configuration']} | {row['Image Recall@1']} | {row['Image Recall@5']} | "
            f"{row['Image Recall@10']} | {row['Image MRR']} |"
        )
        if expected_row not in source:
            raise AssertionError(f"영문 원고 Table III 불일치: {expected_row}")

    for group in ("G3", "G4"):
        row = final_summary[group]
        for metric in ("Image Recall@1", "Image Recall@5", "Image Recall@10", "Image MRR"):
            if row[metric] not in source:
                raise AssertionError(f"영문 원고에 {group} {metric}={row[metric]}가 없습니다.")

    print("PASS: 최종 G3/G4, Table III, bootstrap 근거와 영문 원고 수치가 일치합니다.")


if __name__ == "__main__":
    main()
