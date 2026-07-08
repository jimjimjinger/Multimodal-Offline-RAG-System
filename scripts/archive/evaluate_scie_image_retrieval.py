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
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "07_pilot_image_retrieval_results.csv"
REPORT_OUTPUT_PATH = SCIE_DIR / "07_image_only_pilot_results.md"


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f)]
    return rows


def grade_rank(expected_image, retrieved_images):
    for rank, image in enumerate(retrieved_images[:IMAGE_PARTIAL_LIMIT], start=1):
        if image.get("name") == expected_image:
            return rank, "O" if rank <= IMAGE_O_LIMIT else PARTIAL
    return "", "X"


def reciprocal_rank(rank):
    return 0.0 if not rank else 1.0 / int(rank)


def percent(value):
    return f"{value * 100:.1f}%"


def summarize(rows):
    total = len(rows)
    ranks = [int(row["정답 순위"]) for row in rows if row["정답 순위"]]
    counts = Counter(row["이미지 평가"] for row in rows)

    recall_at_1 = sum(1 for rank in ranks if rank <= 1) / total if total else 0.0
    recall_at_5 = sum(1 for rank in ranks if rank <= 5) / total if total else 0.0
    recall_at_10 = sum(1 for rank in ranks if rank <= 10) / total if total else 0.0
    mrr = sum(reciprocal_rank(row["정답 순위"]) for row in rows) / total if total else 0.0

    return {
        "total": total,
        "O": counts["O"],
        PARTIAL: counts[PARTIAL],
        "X": counts["X"],
        "recall_at_1": recall_at_1,
        "recall_at_5": recall_at_5,
        "recall_at_10": recall_at_10,
        "mrr": mrr,
    }


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


def write_report(summary, rows):
    misses = [row for row in rows if row["이미지 평가"] == "X"]
    partials = [row for row in rows if row["이미지 평가"] == PARTIAL]

    lines = [
        "# 1차 파일럿 실험 결과",
        "",
        "## 실험 목적",
        "",
        "현재 구현된 G3 멀티모달 RAG가 70개 질의셋에서 정답 이미지를 얼마나 잘 검색하는지 확인하였다.",
        "",
        "이번 파일럿은 전체 비교군 중 먼저 구현이 완료된 G3를 대상으로 수행했다.",
        "G1 키워드 검색, G2 텍스트 기반 RAG, G4 상황 인지형 멀티모달 RAG는 후속 비교 실험에서 추가한다.",
        "",
        "## 실험 조건",
        "",
        "| 항목 | 내용 |",
        "|---|---|",
        "| 평가 질의셋 | `SCIE용/data/03_question_set_70.csv` |",
        "| 질문 수 | 70개 |",
        "| 비교군 | G3 멀티모달 RAG |",
        "| 텍스트 임베딩 | BGE-M3 |",
        "| 이미지 검색 | 텍스트 연결 이미지 + 페이지 인접 이미지 + 이미지 전용 ChromaDB 컬렉션 통합 |",
        "| 평가 기준 | 정답 이미지가 검색 이미지 Top-10 안에 포함되는지 확인 |",
        "",
        "## 이미지 검색 성능",
        "",
        "| 지표 | 결과 |",
        "|---|---:|",
        f"| Image Recall@1 | {percent(summary['recall_at_1'])} |",
        f"| Image Recall@5 | {percent(summary['recall_at_5'])} |",
        f"| Image Recall@10 | {percent(summary['recall_at_10'])} |",
        f"| Image MRR | {summary['mrr']:.3f} |",
        "",
        "## O/△/X 요약",
        "",
        "| 평가 | 기준 | 개수 | 비율 |",
        "|---|---|---:|---:|",
        f"| O | 정답 이미지가 Top-5 안에 포함 | {summary['O']} | {percent(summary['O'] / summary['total'])} |",
        f"| △ | 정답 이미지가 Top-6부터 Top-10 사이에 포함 | {summary[PARTIAL]} | {percent(summary[PARTIAL] / summary['total'])} |",
        f"| X | 정답 이미지가 Top-10 안에 없음 | {summary['X']} | {percent(summary['X'] / summary['total'])} |",
        f"| 전체 |  | {summary['total']} | 100.0% |",
        "",
        "## 해석",
        "",
        "- Recall@1은 정답 이미지를 첫 번째로 바로 제시하는 능력을 의미한다.",
        "- Recall@5는 실제 앱 화면에서 사용자가 상위 후보 안에서 정답 이미지를 확인할 가능성을 의미한다.",
        "- Recall@10은 검색 후보군 안에 정답 이미지가 포함되는지를 보는 완화된 기준이다.",
        "- MRR은 정답 이미지가 상위 순위에 얼마나 빨리 등장하는지를 반영한다.",
        "",
        "## 후속 개선 필요 항목",
        "",
        "현재 파일럿 결과에서 X가 나온 질문은 이미지 후보 생성 또는 재정렬 과정에서 정답 이미지가 충분히 위로 올라오지 못한 경우이다.",
        "다음 단계에서는 실습 단계 라벨을 활용한 G4 re-ranking을 추가하여 G3 대비 Recall@5와 MRR이 개선되는지 확인한다.",
        "",
        "## 상세 결과 파일",
        "",
        "- `SCIE용/data/07_pilot_image_retrieval_results.csv`",
        "- `SCIE용/excel/07_pilot_image_retrieval_results.xlsx`",
    ]

    if partials:
        lines.extend(
            [
                "",
                "## △ 사례",
                "",
                "| 질문 번호 | 정답 이미지 | 정답 순위 |",
                "|---|---|---:|",
            ]
        )
        for row in partials:
            lines.append(f"| {row['질문 번호']} | `{row['정답 이미지']}` | {row['정답 순위']} |")

    if misses:
        lines.extend(
            [
                "",
                "## X 사례",
                "",
                "| 질문 번호 | 정답 이미지 | 실습 단계 |",
                "|---|---|---|",
            ]
        )
        for row in misses:
            lines.append(f"| {row['질문 번호']} | `{row['정답 이미지']}` | {row['실습 단계']} |")

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

    summary = summarize(rows)
    write_detail(rows)
    write_report(summary, rows)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"report: {REPORT_OUTPUT_PATH}")
    print(
        "metrics: "
        f"R@1={summary['recall_at_1']:.3f} "
        f"R@5={summary['recall_at_5']:.3f} "
        f"R@10={summary['recall_at_10']:.3f} "
        f"MRR={summary['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()
