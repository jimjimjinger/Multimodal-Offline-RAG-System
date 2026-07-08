import csv
import json
import sys
from collections import Counter
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from evaluate_scie_retrieval import (  # noqa: E402
    IMAGE_PARTIAL_LIMIT,
    IMAGE_COLLECTION_TOP_K,
    IMAGE_RESULTS_LIMIT,
    IMAGE_TEXT_TOP_K,
    PARTIAL,
    TEXT_TOP_K,
    image_rank,
    read_questions,
    reciprocal_rank,
    text_rank,
)
from paths import (  # noqa: E402
    SCIE_DATA_DIR,
    SCIE_DIR,
    SCIE_EXCEL_DIR,
    STAGE_CONTEXT_MAP_MANUAL_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
)
from rag_search import open_rag_collections, retrieve_multimodal  # noqa: E402


USE_MANUAL_CONTEXT_MAP = "--manual" in sys.argv
STAGE_CONTEXT_MAP_FOR_EVAL = STAGE_CONTEXT_MAP_MANUAL_PATH if USE_MANUAL_CONTEXT_MAP else None
G3_DETAIL_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / (
    "12_g4_manual_retrieval_results.csv" if USE_MANUAL_CONTEXT_MAP else "10_g4_retrieval_results.csv"
)
EXCEL_OUTPUT_PATH = SCIE_EXCEL_DIR / (
    "12_g4_manual_retrieval_results.xlsx" if USE_MANUAL_CONTEXT_MAP else "10_g4_retrieval_results.xlsx"
)
REPORT_OUTPUT_PATH = SCIE_DIR / (
    "12_g4_manual_results.md" if USE_MANUAL_CONTEXT_MAP else "10_g4_results.md"
)
REPORT_TITLE = (
    "# G4 매뉴얼 기준 상황 인지형 멀티모달 RAG 평가 결과"
    if USE_MANUAL_CONTEXT_MAP
    else "# G4 상황 인지형 멀티모달 RAG 구현 결과"
)
REPORT_NOTE = (
    "이번 결과는 정답 텍스트/정답 페이지/정답 이미지 파일명을 사용하지 않고, "
    "`11_stage_context_map_manual`의 매뉴얼 기준 단계 문맥표만 사용해 산출한 결과입니다."
    if USE_MANUAL_CONTEXT_MAP
    else "주의: 이번 결과는 1차 구현 검증용입니다. 현재 `09_stage_context_map`은 질의셋의 정답 텍스트 페이지를 근거로 생성한 초안이므로, 논문 본 실험에서는 매뉴얼 기준으로 사전에 확정한 매핑표를 사용하고 평가 후에는 수정하지 않는 절차가 필요합니다."
)
CONTEXT_MAP_LABEL = "11_stage_context_map_manual" if USE_MANUAL_CONTEXT_MAP else "09_stage_context_map"


CSV_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "실습 단계",
    "질문 유형",
    "정답 텍스트",
    "G3 텍스트 정답 순위",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "G4 텍스트 평가 근거",
    "G4 검색 텍스트 Top-10",
    "정답 이미지",
    "G3 이미지 정답 순위",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
    "G4 검색 이미지 Top-10",
]

EXCEL_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "실습 단계",
    "질문 유형",
    "정답 텍스트",
    "G3 텍스트 정답 순위",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "G4 텍스트 평가 근거",
    "정답 이미지",
    "G3 이미지 정답 순위",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
    "G4 검색 이미지 Top-10",
]


def read_detail(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def summarize(rows, rank_key, grade_key):
    total = len(rows)
    ranks = [int(row[rank_key]) for row in rows if str(row.get(rank_key, "")).strip()]
    counts = Counter(row.get(grade_key, "") for row in rows)
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


def metric_delta(new_value, old_value):
    delta = new_value - old_value
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta * 100:.1f}%p"


def score_delta(new_value, old_value):
    delta = new_value - old_value
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.3f}"


def rank_delta(new_rank, old_rank):
    if not new_rank or not old_rank:
        return ""
    return int(old_rank) - int(new_rank)


def both_at(rows, text_rank_key, image_rank_key, limit):
    return sum(
        1
        for row in rows
        if row.get(text_rank_key)
        and int(row[text_rank_key]) <= limit
        and row.get(image_rank_key)
        and int(row[image_rank_key]) <= limit
    ) / len(rows)


def write_detail(rows):
    DETAIL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DETAIL_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_excel(rows):
    table = [EXCEL_FIELDS]
    for row in rows:
        table.append([row.get(field, "") for field in EXCEL_FIELDS])
    write_workbook(table, EXCEL_OUTPUT_PATH, "G4 검색 평가")


def write_report(g3_text, g3_image, g4_text, g4_image, g3_rows, g4_rows):
    g3_both_5 = both_at(g3_rows, "텍스트 정답 순위", "이미지 정답 순위", 5)
    g3_both_10 = both_at(g3_rows, "텍스트 정답 순위", "이미지 정답 순위", 10)
    g4_both_5 = both_at(g4_rows, "G4 텍스트 정답 순위", "G4 이미지 정답 순위", 5)
    g4_both_10 = both_at(g4_rows, "G4 텍스트 정답 순위", "G4 이미지 정답 순위", 10)

    improved = []
    worsened = []
    for row in g4_rows:
        text_change = rank_delta(row["G4 텍스트 정답 순위"], row["G3 텍스트 정답 순위"])
        image_change = rank_delta(row["G4 이미지 정답 순위"], row["G3 이미지 정답 순위"])
        if text_change or image_change:
            item = {
                "qid": row["질문 번호"],
                "stage": row["실습 단계"],
                "text": text_change,
                "image": image_change,
                "expected_image": row["정답 이미지"],
            }
            if (text_change or 0) > 0 or (image_change or 0) > 0:
                improved.append(item)
            if (text_change or 0) < 0 or (image_change or 0) < 0:
                worsened.append(item)

    lines = [
        REPORT_TITLE,
        "",
        "## 구현 요약",
        "",
        "G4는 기존 G3 멀티모달 RAG에 실습 단계 문맥 매핑표를 추가한 구조입니다.",
        f"질문별 정답 이미지 파일명을 직접 사용하지 않고, `{CONTEXT_MAP_LABEL}`의 단계별 페이지 범위, 섹션 키워드, 본문 키워드를 이용해 텍스트와 이미지 후보를 다시 정렬했습니다.",
        "",
        REPORT_NOTE,
        "",
        "## G3 대비 검색 성능",
        "",
        "### 텍스트 검색",
        "",
        "| 지표 | G3 | G4 | 변화 |",
        "|---|---:|---:|---:|",
        f"| Text Recall@1 | {percent(g3_text['recall_at_1'])} | {percent(g4_text['recall_at_1'])} | {metric_delta(g4_text['recall_at_1'], g3_text['recall_at_1'])} |",
        f"| Text Recall@5 | {percent(g3_text['recall_at_5'])} | {percent(g4_text['recall_at_5'])} | {metric_delta(g4_text['recall_at_5'], g3_text['recall_at_5'])} |",
        f"| Text Recall@10 | {percent(g3_text['recall_at_10'])} | {percent(g4_text['recall_at_10'])} | {metric_delta(g4_text['recall_at_10'], g3_text['recall_at_10'])} |",
        f"| Text MRR | {g3_text['mrr']:.3f} | {g4_text['mrr']:.3f} | {score_delta(g4_text['mrr'], g3_text['mrr'])} |",
        "",
        "### 이미지 검색",
        "",
        "| 지표 | G3 | G4 | 변화 |",
        "|---|---:|---:|---:|",
        f"| Image Recall@1 | {percent(g3_image['recall_at_1'])} | {percent(g4_image['recall_at_1'])} | {metric_delta(g4_image['recall_at_1'], g3_image['recall_at_1'])} |",
        f"| Image Recall@5 | {percent(g3_image['recall_at_5'])} | {percent(g4_image['recall_at_5'])} | {metric_delta(g4_image['recall_at_5'], g3_image['recall_at_5'])} |",
        f"| Image Recall@10 | {percent(g3_image['recall_at_10'])} | {percent(g4_image['recall_at_10'])} | {metric_delta(g4_image['recall_at_10'], g3_image['recall_at_10'])} |",
        f"| Image MRR | {g3_image['mrr']:.3f} | {g4_image['mrr']:.3f} | {score_delta(g4_image['mrr'], g3_image['mrr'])} |",
        "",
        "### 텍스트+이미지 동시 검색",
        "",
        "| 지표 | G3 | G4 | 변화 |",
        "|---|---:|---:|---:|",
        f"| Text + Image Both@5 | {percent(g3_both_5)} | {percent(g4_both_5)} | {metric_delta(g4_both_5, g3_both_5)} |",
        f"| Text + Image Both@10 | {percent(g3_both_10)} | {percent(g4_both_10)} | {metric_delta(g4_both_10, g3_both_10)} |",
        "",
        "## G4 O/△/X 요약",
        "",
        "| 평가 대상 | O | △ | X | 전체 |",
        "|---|---:|---:|---:|---:|",
        f"| 텍스트 | {g4_text['O']} | {g4_text[PARTIAL]} | {g4_text['X']} | {g4_text['total']} |",
        f"| 이미지 | {g4_image['O']} | {g4_image[PARTIAL]} | {g4_image['X']} | {g4_image['total']} |",
        "",
        "## 해석",
        "",
        "- G4는 실습 단계가 주어졌을 때 해당 단계와 가까운 페이지 및 키워드를 가진 후보를 상위로 올리는 방식입니다.",
        "- Recall@k는 정답이 후보 안에 들어오는지를 보고, MRR은 정답이 얼마나 앞 순위에 배치되는지를 봅니다.",
        "- 따라서 Recall이 유지되면서 MRR이나 Recall@1이 올라가면, 같은 후보군 안에서 정답을 더 앞쪽으로 정렬한 효과로 해석할 수 있습니다.",
        "",
        "## 순위 변화 예시",
        "",
        "### 개선된 사례",
        "",
        "| 질문 번호 | 실습 단계 | 텍스트 순위 변화 | 이미지 순위 변화 | 정답 이미지 |",
        "|---|---|---:|---:|---|",
    ]

    for item in improved[:12]:
        lines.append(
            f"| {item['qid']} | {item['stage']} | {item['text'] or 0:+} | "
            f"{item['image'] or 0:+} | `{item['expected_image']}` |"
        )
    if not improved:
        lines.append("| - | - | - | - | - |")

    lines.extend(
        [
            "",
            "### 악화된 사례",
            "",
            "| 질문 번호 | 실습 단계 | 텍스트 순위 변화 | 이미지 순위 변화 | 정답 이미지 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for item in worsened[:12]:
        lines.append(
            f"| {item['qid']} | {item['stage']} | {item['text'] or 0:+} | "
            f"{item['image'] or 0:+} | `{item['expected_image']}` |"
        )
    if not worsened:
        lines.append("| - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            f"- `SCIE용/data/{DETAIL_OUTPUT_PATH.name}`",
            f"- `SCIE용/excel/{EXCEL_OUTPUT_PATH.name}`",
            f"- `SCIE용/{REPORT_OUTPUT_PATH.name}`",
        ]
    )

    REPORT_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_model_cache()
    questions = read_questions()
    g3_rows = read_detail(G3_DETAIL_PATH)
    g3_by_id = {row["질문 번호"]: row for row in g3_rows}

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
            answer_top_k=TEXT_TOP_K,
            image_text_top_k=IMAGE_TEXT_TOP_K,
            image_collection_top_k=IMAGE_COLLECTION_TOP_K,
            image_results_limit=IMAGE_RESULTS_LIMIT,
            stage_label=question["실습 단계"],
            stage_context_map_path=STAGE_CONTEXT_MAP_FOR_EVAL,
        )

        t_rank, t_grade, t_reason, t_details = text_rank(
            expected_answer=question["정답 텍스트"],
            expected_page=question["페이지"],
            ids=retrieval["answer_ids"][:TEXT_TOP_K],
            docs=retrieval["answer_docs"][:TEXT_TOP_K],
            metas=retrieval["answer_metas"][:TEXT_TOP_K],
            embedder=embedder,
            text_collection=text_collection,
        )
        i_rank, i_grade = image_rank(question["정답 이미지"], retrieval["images"])

        g3 = g3_by_id.get(question["질문 번호"], {})
        row = {
            "질문 번호": question["질문 번호"],
            "구분": question["구분"],
            "질문": question["질문"],
            "실습 단계": question["실습 단계"],
            "질문 유형": question["질문 유형"],
            "정답 텍스트": question["정답 텍스트"],
            "G3 텍스트 정답 순위": g3.get("텍스트 정답 순위", ""),
            "G4 텍스트 정답 순위": t_rank,
            "G4 텍스트 평가": t_grade,
            "G4 텍스트 평가 근거": t_reason,
            "G4 검색 텍스트 Top-10": "\n".join(
                f"{item['rank']}. {item['heading']} | pages {item['pages']} | "
                f"{item['reason']} | stage={item.get('stage_reason', '')} | {item['preview']}"
                for item in t_details
            ),
            "정답 이미지": question["정답 이미지"],
            "G3 이미지 정답 순위": g3.get("이미지 정답 순위", ""),
            "G4 이미지 정답 순위": i_rank,
            "G4 이미지 평가": i_grade,
            "G4 검색 이미지 Top-10": "\n".join(
                f"{i}. {image['name']} | score={image['score']:.3f} | "
                f"stage={image.get('stage_score', 0):.3f} | {image.get('stage_reason', '')}"
                for i, image in enumerate(retrieval["images"][:IMAGE_PARTIAL_LIMIT], start=1)
            ),
        }
        rows.append(row)
        print(
            f"[{idx}/{len(questions)}] {question['질문 번호']} "
            f"text={t_rank or '-'}:{t_grade} image={i_rank or '-'}:{i_grade}",
            flush=True,
        )

    g3_text = summarize(g3_rows, "텍스트 정답 순위", "텍스트 평가")
    g3_image = summarize(g3_rows, "이미지 정답 순위", "이미지 평가")
    g4_text = summarize(rows, "G4 텍스트 정답 순위", "G4 텍스트 평가")
    g4_image = summarize(rows, "G4 이미지 정답 순위", "G4 이미지 평가")

    write_detail(rows)
    write_excel(rows)
    write_report(g3_text, g3_image, g4_text, g4_image, g3_rows, rows)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"excel: {EXCEL_OUTPUT_PATH}")
    print(f"report: {REPORT_OUTPUT_PATH}")
    print(
        "g4 text metrics: "
        f"R@1={g4_text['recall_at_1']:.3f} "
        f"R@5={g4_text['recall_at_5']:.3f} "
        f"R@10={g4_text['recall_at_10']:.3f} "
        f"MRR={g4_text['mrr']:.3f}"
    )
    print(
        "g4 image metrics: "
        f"R@1={g4_image['recall_at_1']:.3f} "
        f"R@5={g4_image['recall_at_5']:.3f} "
        f"R@10={g4_image['recall_at_10']:.3f} "
        f"MRR={g4_image['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()
