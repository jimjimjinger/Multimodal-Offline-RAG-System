import csv
import json
import sys
from collections import Counter
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import VECTOR_DB_DIR, configure_model_cache  # noqa: E402
from rag_search import open_rag_collections, retrieve_multimodal  # noqa: E402


IMAGE_O_LIMIT = 5
IMAGE_PARTIAL_LIMIT = 10
PARTIAL = "△"


def find_scie_dir():
    return next(path for path in PROJECT_ROOT.iterdir() if path.is_dir() and path.name.startswith("SCIE"))


SCIE_DIR = find_scie_dir()
SCIE_DATA_DIR = SCIE_DIR / "data"
SCIE_EXCEL_DIR = SCIE_DIR / "excel"
QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
G3_DETAIL_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "08_context_image_retrieval_results.csv"
REPORT_OUTPUT_PATH = SCIE_DIR / "08_stage_label_pilot_results.md"


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_detail(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def grade_rank(expected_image, retrieved_images):
    for rank, image in enumerate(retrieved_images[:IMAGE_PARTIAL_LIMIT], start=1):
        if image.get("name") == expected_image:
            return rank, "O" if rank <= IMAGE_O_LIMIT else PARTIAL
    return "", "X"


def reciprocal_rank(rank):
    return 0.0 if not rank else 1.0 / int(rank)


def summarize(rows):
    total = len(rows)
    rank_key = "정답 순위" if "정답 순위" in rows[0] else "이미지 정답 순위"
    grade_key = "이미지 평가"
    ranks = [int(row[rank_key]) for row in rows if row[rank_key]]
    counts = Counter(row[grade_key] for row in rows)
    return {
        "total": total,
        "O": counts["O"],
        PARTIAL: counts[PARTIAL],
        "X": counts["X"],
        "recall_at_1": sum(1 for rank in ranks if rank <= 1) / total if total else 0.0,
        "recall_at_5": sum(1 for rank in ranks if rank <= 5) / total if total else 0.0,
        "recall_at_10": sum(1 for rank in ranks if rank <= 10) / total if total else 0.0,
        "mrr": sum(reciprocal_rank(row[rank_key]) for row in rows) / total if total else 0.0,
    }


def percent(value):
    return f"{value * 100:.1f}%"


def write_detail(rows):
    fields = [
        "질문 번호",
        "구분",
        "질문",
        "실습 단계",
        "질문 유형",
        "정답 이미지",
        "정답 순위",
        "이미지 평가",
        "검색 이미지 Top-10",
        "검색 상세 JSON",
    ]
    with DETAIL_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metric_delta(new_value, old_value):
    if old_value is None:
        return "-"
    delta = new_value - old_value
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta * 100:.1f}%p"


def score_delta(new_value, old_value):
    if old_value is None:
        return "-"
    delta = new_value - old_value
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.3f}"


def grade_changes(g3_rows, g4_rows):
    g3_by_qid = {row["질문 번호"]: row for row in g3_rows}
    changes = []
    for row in g4_rows:
        before = g3_by_qid.get(row["질문 번호"])
        if not before:
            continue
        before_rank_value = before.get("정답 순위", before.get("이미지 정답 순위", ""))
        before_rank = before_rank_value or "-"
        after_rank = str(row["정답 순위"] or "-")
        if before["이미지 평가"] != row["이미지 평가"] or before_rank != after_rank:
            changes.append(
                {
                    "qid": row["질문 번호"],
                    "stage": row["실습 단계"],
                    "expected": row["정답 이미지"],
                    "before_rank": before_rank,
                    "before_grade": before["이미지 평가"],
                    "after_rank": after_rank,
                    "after_grade": row["이미지 평가"],
                }
            )
    return changes


def write_report(g3_summary, g4_summary, g3_rows, g4_rows):
    has_g3 = bool(g3_rows)
    lines = [
        "# 실습 단계 라벨 re-ranking 파일럿 결과",
        "",
        "## 실험 목적",
        "",
        "이 파일은 정식 G4 상황 인지형 멀티모달 RAG 결과가 아니라, G4 구현 전에 수행한 파일럿 결과이다.",
        "70개 질의셋의 `실습 단계` 값을 검색 입력으로 단순 추가했을 때 정답 이미지 순위가 개선되는지 확인하였다.",
        "",
        "정식 G4로 보기 위해서는 실습 단계별 page 범위, section, keyword 매핑표를 먼저 구축해야 한다.",
        "",
        "## 구현 방식",
        "",
        "이 파일럿에서는 정답 이미지 파일명을 직접 사용하지 않았다.",
        "대신 각 질문의 실습 단계 라벨을 이용해 다음 두 가지를 추가하였다.",
        "",
        "1. `실습 단계 + 질문` 문장으로 이미지 컬렉션을 추가 검색한다.",
        "2. 후보 이미지의 heading, page, 주변 텍스트가 실습 단계 단어와 얼마나 맞는지 re-ranking 점수에 반영한다.",
        "",
        "## G3 대비 파일럿 검색 성능 비교",
        "",
        "| 지표 | G3 멀티모달 RAG | 실습 단계 라벨 파일럿 | 변화 |",
        "|---|---:|---:|---:|",
    ]

    if has_g3:
        lines.extend(
            [
                f"| Image Recall@1 | {percent(g3_summary['recall_at_1'])} | {percent(g4_summary['recall_at_1'])} | {metric_delta(g4_summary['recall_at_1'], g3_summary['recall_at_1'])} |",
                f"| Image Recall@5 | {percent(g3_summary['recall_at_5'])} | {percent(g4_summary['recall_at_5'])} | {metric_delta(g4_summary['recall_at_5'], g3_summary['recall_at_5'])} |",
                f"| Image Recall@10 | {percent(g3_summary['recall_at_10'])} | {percent(g4_summary['recall_at_10'])} | {metric_delta(g4_summary['recall_at_10'], g3_summary['recall_at_10'])} |",
                f"| Image MRR | {g3_summary['mrr']:.3f} | {g4_summary['mrr']:.3f} | {score_delta(g4_summary['mrr'], g3_summary['mrr'])} |",
            ]
        )
    else:
        lines.extend(
            [
                f"| Image Recall@1 | - | {percent(g4_summary['recall_at_1'])} | - |",
                f"| Image Recall@5 | - | {percent(g4_summary['recall_at_5'])} | - |",
                f"| Image Recall@10 | - | {percent(g4_summary['recall_at_10'])} | - |",
                f"| Image MRR | - | {g4_summary['mrr']:.3f} | - |",
            ]
        )

    lines.extend(
        [
            "",
            "## 파일럿 O/△/X 요약",
            "",
            "| 평가 | 기준 | 개수 | 비율 |",
            "|---|---|---:|---:|",
            f"| O | 정답 이미지가 Top-5 안에 포함 | {g4_summary['O']} | {percent(g4_summary['O'] / g4_summary['total'])} |",
            f"| △ | 정답 이미지가 Top-6부터 Top-10 사이에 포함 | {g4_summary[PARTIAL]} | {percent(g4_summary[PARTIAL] / g4_summary['total'])} |",
            f"| X | 정답 이미지가 Top-10 안에 없음 | {g4_summary['X']} | {percent(g4_summary['X'] / g4_summary['total'])} |",
            f"| 전체 |  | {g4_summary['total']} | 100.0% |",
            "",
            "## 해석",
            "",
            "이 파일럿의 핵심 판단 기준은 G3 대비 Recall@5와 MRR이 개선되는지이다.",
            "Recall@5가 증가하면 사용자가 상위 후보 안에서 정답 이미지를 확인할 가능성이 높아졌다는 의미이고, MRR이 증가하면 정답 이미지가 더 앞쪽 순위로 올라왔다는 의미이다.",
            "",
            "이번 파일럿에서는 실습 단계 라벨을 단순히 검색어와 점수 가중치로 반영했을 때 G3 대비 Recall@5와 Recall@10을 개선하지 못했고, Recall@1과 MRR은 소폭 감소하였다.",
            "따라서 현재의 실습 단계 라벨을 단순 검색어와 점수 가중치로만 사용하는 방식은 충분하지 않다고 판단한다.",
            "정식 G4를 구현하려면 실습 단계 라벨을 매뉴얼 section/page 범위와 명시적으로 연결하거나, 단계별 keyword 사전을 별도로 구성한 뒤 다시 평가할 필요가 있다.",
            "",
            "## 상세 결과 파일",
            "",
            "- `SCIE용/data/08_context_image_retrieval_results.csv`",
            "- `SCIE용/excel/08_context_image_retrieval_results.xlsx`",
        ]
    )

    changes = grade_changes(g3_rows, g4_rows)
    if changes:
        lines.extend(
            [
                "",
                "## G3 대비 순위 변화 사례",
                "",
                "| 질문 번호 | 정답 이미지 | 실습 단계 | G3 순위/평가 | 파일럿 순위/평가 |",
                "|---|---|---|---|---|",
            ]
        )
        for item in changes[:30]:
            lines.append(
                f"| {item['qid']} | `{item['expected']}` | {item['stage']} | "
                f"{item['before_rank']} / {item['before_grade']} | {item['after_rank']} / {item['after_grade']} |"
            )

    REPORT_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_model_cache()
    questions = read_questions()

    embedder = SentenceTransformer("BAAI/bge-m3")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)

    rows = []
    for idx, question in enumerate(questions, start=1):
        retrieval = retrieve_multimodal(
            question=question["질문"],
            embedder=embedder,
            text_collection=text_collection,
            image_collection=image_collection,
            stage_label=question["실습 단계"],
        )
        images = retrieval["images"]
        rank, grade = grade_rank(question["정답 이미지"], images)
        top_names = [image["name"] for image in images[:IMAGE_PARTIAL_LIMIT]]
        rows.append(
            {
                "질문 번호": question["질문 번호"],
                "구분": question["구분"],
                "질문": question["질문"],
                "실습 단계": question["실습 단계"],
                "질문 유형": question["질문 유형"],
                "정답 이미지": question["정답 이미지"],
                "정답 순위": rank,
                "이미지 평가": grade,
                "검색 이미지 Top-10": "\n".join(f"{i}. {name}" for i, name in enumerate(top_names, start=1)),
                "검색 상세 JSON": json.dumps(images[:IMAGE_PARTIAL_LIMIT], ensure_ascii=False),
            }
        )
        print(f"[{idx}/{len(questions)}] {question['질문 번호']} rank={rank or '-'} grade={grade}", flush=True)

    g3_rows = read_detail(G3_DETAIL_PATH)
    g3_summary = summarize(g3_rows) if g3_rows else None
    g4_summary = summarize(rows)
    write_detail(rows)
    write_report(g3_summary, g4_summary, g3_rows, rows)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"report: {REPORT_OUTPUT_PATH}")
    print(
        "metrics: "
        f"R@1={g4_summary['recall_at_1']:.3f} "
        f"R@5={g4_summary['recall_at_5']:.3f} "
        f"R@10={g4_summary['recall_at_10']:.3f} "
        f"MRR={g4_summary['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()
