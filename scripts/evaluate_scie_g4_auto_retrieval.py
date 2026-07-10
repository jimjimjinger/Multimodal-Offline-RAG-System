import csv
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
from stage_classifier import build_stage_profiles, classify_stage, encode_stage_profiles  # noqa: E402


G3_DETAIL_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
ORACLE_G4_DETAIL_PATH = SCIE_DATA_DIR / "12_g4_manual_retrieval_results.csv"
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "30_g4_auto_retrieval_results.csv"
EXCEL_OUTPUT_PATH = SCIE_EXCEL_DIR / "30_g4_auto_retrieval_results.xlsx"
REPORT_OUTPUT_PATH = SCIE_DIR / "30_g4_auto_results.md"

CSV_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "정답 실습 단계",
    "예측 실습 단계",
    "G4 적용 단계",
    "분류 점수",
    "분류 margin",
    "G4 적용",
    "정답 텍스트",
    "G3 텍스트 정답 순위",
    "G4-oracle 텍스트 정답 순위",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "G4 텍스트 평가 근거",
    "정답 이미지",
    "G3 이미지 정답 순위",
    "G4-oracle 이미지 정답 순위",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
    "G4 검색 이미지 Top-10",
]

EXCEL_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "정답 실습 단계",
    "예측 실습 단계",
    "G4 적용 단계",
    "분류 점수",
    "분류 margin",
    "G4 적용",
    "정답 텍스트",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "정답 이미지",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
    "G4 검색 이미지 Top-10",
]


def read_detail(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_detail(rows):
    DETAIL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DETAIL_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_excel(rows):
    table = [EXCEL_FIELDS] + [[row.get(field, "") for field in EXCEL_FIELDS] for row in rows]
    write_workbook(table, EXCEL_OUTPUT_PATH, "G4-auto 검색 평가")


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


def both_at(rows, text_rank_key, image_rank_key, limit):
    if not rows:
        return 0.0
    return sum(
        1
        for row in rows
        if row.get(text_rank_key)
        and int(row[text_rank_key]) <= limit
        and row.get(image_rank_key)
        and int(row[image_rank_key]) <= limit
    ) / len(rows)


def metric_row(label, text_summary, image_summary, rows, text_key, image_key):
    return {
        "label": label,
        "text_r1": text_summary["recall_at_1"],
        "text_r5": text_summary["recall_at_5"],
        "text_r10": text_summary["recall_at_10"],
        "text_mrr": text_summary["mrr"],
        "image_r1": image_summary["recall_at_1"],
        "image_r5": image_summary["recall_at_5"],
        "image_r10": image_summary["recall_at_10"],
        "image_mrr": image_summary["mrr"],
        "both5": both_at(rows, text_key, image_key, 5),
        "both10": both_at(rows, text_key, image_key, 10),
    }


def write_report(rows, g3_rows, oracle_rows):
    g3_text = summarize(g3_rows, "텍스트 정답 순위", "텍스트 평가")
    g3_image = summarize(g3_rows, "이미지 정답 순위", "이미지 평가")
    oracle_text = summarize(oracle_rows, "G4 텍스트 정답 순위", "G4 텍스트 평가")
    oracle_image = summarize(oracle_rows, "G4 이미지 정답 순위", "G4 이미지 평가")
    auto_text = summarize(rows, "G4 텍스트 정답 순위", "G4 텍스트 평가")
    auto_image = summarize(rows, "G4 이미지 정답 순위", "G4 이미지 평가")

    metrics = [
        metric_row("G3", g3_text, g3_image, g3_rows, "텍스트 정답 순위", "이미지 정답 순위"),
        metric_row("G4", auto_text, auto_image, rows, "G4 텍스트 정답 순위", "G4 이미지 정답 순위"),
    ]
    oracle_metric = metric_row(
        "G4 oracle-stage",
        oracle_text,
        oracle_image,
        oracle_rows,
        "G4 텍스트 정답 순위",
        "G4 이미지 정답 순위",
    )
    applied = sum(1 for row in rows if row["G4 적용"] == "O")
    correct_stage = sum(1 for row in rows if row["예측 실습 단계"] == row["정답 실습 단계"])

    lines = [
        "# G4 검색 평가 결과",
        "",
        "## 평가 개요",
        "",
        "본 문서에서 G4는 사용자가 실습 단계를 직접 선택하지 않고, 질문과 실습 단계 context profile 간 BGE-M3 의미 유사도를 이용해 단계를 추정한 뒤 G4 re-ranking을 적용하는 방식이다.",
        "분류 결과가 낮은 신뢰도 또는 애매한 후보로 판단되면 stage_label을 적용하지 않고 G3와 동일하게 검색한다.",
        "",
        "## 단계 추정 요약",
        "",
        f"- Top-1 stage accuracy: {percent(correct_stage / len(rows))} ({correct_stage}/{len(rows)})",
        f"- G4 적용률: {percent(applied / len(rows))} ({applied}/{len(rows)})",
        "",
        "## 검색 성능 비교",
        "",
        "| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in metrics:
        lines.append(
            f"| {item['label']} | {percent(item['text_r1'])} | {percent(item['text_r5'])} | "
            f"{percent(item['text_r10'])} | {item['text_mrr']:.3f} | "
            f"{percent(item['image_r1'])} | {percent(item['image_r5'])} | "
            f"{percent(item['image_r10'])} | {item['image_mrr']:.3f} | "
            f"{percent(item['both5'])} | {percent(item['both10'])} |"
        )

    lines.extend(
        [
            "",
            "## 해석",
            "",
            "- G4는 실제 앱 사용 조건에 가까운 단계 추정 기반 성능이다.",
            "- G4가 G3보다 높게 나타났으므로, 단계 추정 기반 context-aware re-ranking이 이미지 검색 순위 개선에 기여한 것으로 해석할 수 있다.",
            "- 정답 실습 단계를 미리 알고 적용한 oracle-stage 결과는 본문 메인 비교에 포함하지 않고, 필요한 경우 추가 분석 또는 부록에서 상한 성능으로만 언급한다.",
            "",
            "## 참고: oracle-stage 상한 성능",
            "",
            f"정답 실습 단계가 주어졌다고 가정하면 Text R@1 {percent(oracle_metric['text_r1'])}, "
            f"Image R@5 {percent(oracle_metric['image_r5'])}, Image R@10 {percent(oracle_metric['image_r10'])}, "
            f"Image MRR {oracle_metric['image_mrr']:.3f}까지 상승한다. 이 결과는 실제 앱 성능이 아니라 단계 인식이 더 정확해질 경우 도달 가능한 상한선으로만 해석한다.",
            "",
            "## 산출 파일",
            "",
            f"- `{DETAIL_OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{EXCEL_OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        ]
    )
    REPORT_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_model_cache()
    questions = read_questions()
    g3_rows = read_detail(G3_DETAIL_PATH)
    oracle_rows = read_detail(ORACLE_G4_DETAIL_PATH)
    g3_by_id = {row["질문 번호"]: row for row in g3_rows}
    oracle_by_id = {row["질문 번호"]: row for row in oracle_rows}

    embedder = SentenceTransformer("BAAI/bge-m3")
    profiles = build_stage_profiles(STAGE_CONTEXT_MAP_MANUAL_PATH)
    profile_embeddings = encode_stage_profiles(embedder, profiles)

    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)

    rows = []
    for idx, question in enumerate(questions, start=1):
        classification = classify_stage(
            question=question["질문"],
            embedder=embedder,
            profiles=profiles,
            profile_embeddings=profile_embeddings,
            top_k=5,
        )
        stage_label = classification["stage_label"]
        retrieval = retrieve_multimodal(
            question=question["질문"],
            embedder=embedder,
            text_collection=text_collection,
            image_collection=image_collection,
            answer_top_k=TEXT_TOP_K,
            image_text_top_k=IMAGE_TEXT_TOP_K,
            image_collection_top_k=IMAGE_COLLECTION_TOP_K,
            image_results_limit=IMAGE_RESULTS_LIMIT,
            stage_label=stage_label,
            stage_context_map_path=STAGE_CONTEXT_MAP_MANUAL_PATH if stage_label else None,
        )
        t_rank, t_grade, t_reason, _ = text_rank(
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
        oracle = oracle_by_id.get(question["질문 번호"], {})
        rows.append(
            {
                "질문 번호": question["질문 번호"],
                "구분": question["구분"],
                "질문": question["질문"],
                "정답 실습 단계": question["실습 단계"],
                "예측 실습 단계": classification["predicted_stage"],
                "G4 적용 단계": stage_label or "",
                "분류 점수": f"{classification['score']:.4f}",
                "분류 margin": f"{classification['margin']:.4f}",
                "G4 적용": "O" if classification["used"] else "X",
                "정답 텍스트": question["정답 텍스트"],
                "G3 텍스트 정답 순위": g3.get("텍스트 정답 순위", ""),
                "G4-oracle 텍스트 정답 순위": oracle.get("G4 텍스트 정답 순위", ""),
                "G4 텍스트 정답 순위": t_rank,
                "G4 텍스트 평가": t_grade,
                "G4 텍스트 평가 근거": t_reason,
                "정답 이미지": question["정답 이미지"],
                "G3 이미지 정답 순위": g3.get("이미지 정답 순위", ""),
                "G4-oracle 이미지 정답 순위": oracle.get("G4 이미지 정답 순위", ""),
                "G4 이미지 정답 순위": i_rank,
                "G4 이미지 평가": i_grade,
                "G4 검색 이미지 Top-10": "\n".join(
                    f"{i}. {image['name']} | score={image['score']:.3f} | "
                    f"stage={image.get('stage_score', 0):.3f} | {image.get('stage_reason', '')}"
                    for i, image in enumerate(retrieval["images"][:IMAGE_PARTIAL_LIMIT], start=1)
                ),
            }
        )
        print(
            f"[{idx}/{len(questions)}] {question['질문 번호']} "
            f"stage={stage_label or '-'} text={t_rank or '-'}:{t_grade} image={i_rank or '-'}:{i_grade}",
            flush=True,
        )

    write_detail(rows)
    write_excel(rows)
    write_report(rows, g3_rows, oracle_rows)
    print(f"created: {DETAIL_OUTPUT_PATH}")
    print(f"created: {EXCEL_OUTPUT_PATH}")
    print(f"created: {REPORT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
