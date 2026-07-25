import csv
import json
import math
import re
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
    TEXT_TOP_K,
    both_at,
    clean_csv_rows,
    summarize_rank,
    text_rank,
)
from paths import (  # noqa: E402
    BGE_M3_MODEL_ID,
    SCIE_DATA_DIR,
    SCIE_DIR,
    SCIE_EXCEL_DIR,
    TEXT_CHUNKS_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
)
from rag_search import TEXT_COLLECTION_NAME, query_first  # noqa: E402


QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
G3_DETAIL_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
G4_DETAIL_PATH = SCIE_DATA_DIR / "30_g4_auto_retrieval_results.csv"

DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "15_g1_g2_g3_g4_retrieval_results.csv"
EXCEL_OUTPUT_PATH = SCIE_EXCEL_DIR / "15_g1_g2_g3_g4_retrieval_results.xlsx"
SUMMARY_CSV_PATH = SCIE_DATA_DIR / "15_g1_g2_g3_g4_summary.csv"
SUMMARY_XLSX_PATH = SCIE_EXCEL_DIR / "15_g1_g2_g3_g4_summary.xlsx"
REPORT_OUTPUT_PATH = SCIE_DIR / "15_g1_g2_g3_g4_results.md"

TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
TEXT_TOP_DEBUG = 10

STOPWORDS = {
    "것",
    "수",
    "및",
    "또는",
    "그리고",
    "위해",
    "통해",
    "경우",
    "관련",
    "사용",
    "설정",
    "가능",
    "필요",
    "권장",
    "확인",
    "입력",
    "출력",
    "무엇",
    "어떻게",
    "얼마",
    "로봇",
    "제어기",
    "컨트롤러",
    "시스템",
    "두산로보틱스",
}


GROUPS = {
    "G1": "키워드 기반 단순 검색",
    "G2": "텍스트 기반 RAG",
    "G3": "멀티모달 RAG",
    "G4": "단계 추정 기반 상황 인지형 멀티모달 RAG",
}


DETAIL_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "실습 단계",
    "질문 유형",
    "정답 텍스트",
    "정답 이미지",
    "G1 텍스트 정답 순위",
    "G1 텍스트 평가",
    "G1 텍스트 평가 근거",
    "G1 검색 텍스트 Top-10",
    "G2 텍스트 정답 순위",
    "G2 텍스트 평가",
    "G2 텍스트 평가 근거",
    "G2 검색 텍스트 Top-10",
    "G3 텍스트 정답 순위",
    "G3 텍스트 평가",
    "G3 이미지 정답 순위",
    "G3 이미지 평가",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
]

EXCEL_FIELDS = [
    "질문 번호",
    "구분",
    "질문",
    "실습 단계",
    "질문 유형",
    "정답 텍스트",
    "정답 이미지",
    "G1 텍스트 정답 순위",
    "G1 텍스트 평가",
    "G2 텍스트 정답 순위",
    "G2 텍스트 평가",
    "G3 텍스트 정답 순위",
    "G3 텍스트 평가",
    "G3 이미지 정답 순위",
    "G3 이미지 평가",
    "G4 텍스트 정답 순위",
    "G4 텍스트 평가",
    "G4 이미지 정답 순위",
    "G4 이미지 평가",
]

SUMMARY_FIELDS = [
    "비교군",
    "설명",
    "Text Recall@1",
    "Text Recall@5",
    "Text Recall@10",
    "Text MRR",
    "Image Recall@1",
    "Image Recall@5",
    "Image Recall@10",
    "Image MRR",
    "Both@5",
    "Both@10",
]


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def percent(value):
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def score(value):
    if value is None:
        return "-"
    return f"{value:.3f}"


def normalize_text(value):
    return str(value or "").lower()


def tokens(value):
    results = []
    for token in TOKEN_RE.findall(normalize_text(value)):
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        results.append(token)
    return results


def load_text_chunks():
    chunks = json.loads(TEXT_CHUNKS_PATH.read_text(encoding="utf-8"))
    docs = []
    document_frequency = Counter()
    for index, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        heading = chunk.get("heading", "")
        pages = chunk.get("pages", [])
        doc_tokens = tokens(f"{heading} {text}")
        token_counts = Counter(doc_tokens)
        for token in token_counts:
            document_frequency[token] += 1
        docs.append(
            {
                "id": f"chunk_{index}",
                "doc": text,
                "meta": {"heading": heading, "pages": json.dumps(pages, ensure_ascii=False)},
                "token_counts": token_counts,
                "length": max(1, len(doc_tokens)),
            }
        )
    return docs, document_frequency


def keyword_search(question, docs, document_frequency, limit=TEXT_TOP_K):
    query_terms = tokens(question)
    if not query_terms:
        return [], [], []

    total_docs = max(1, len(docs))
    avg_len = sum(doc["length"] for doc in docs) / total_docs
    scored = []
    for doc in docs:
        score_value = 0.0
        for term in query_terms:
            term_frequency = doc["token_counts"].get(term, 0)
            if not term_frequency:
                continue
            doc_frequency = document_frequency.get(term, 0)
            idf = math.log(1 + ((total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5)))
            numerator = term_frequency * 2.2
            denominator = term_frequency + 1.2 * (1 - 0.75 + 0.75 * (doc["length"] / avg_len))
            score_value += idf * (numerator / denominator)

        if score_value > 0:
            scored.append((score_value, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_docs = [doc for _, doc in scored[:limit]]
    return (
        [doc["id"] for doc in top_docs],
        [doc["doc"] for doc in top_docs],
        [doc["meta"] for doc in top_docs],
    )


def text_embedding_search(question, embedder, text_collection, limit=TEXT_TOP_K):
    query_embedding = embedder.encode(question).tolist()
    result = text_collection.query(query_embeddings=[query_embedding], n_results=limit)
    return (
        query_first(result, "ids"),
        query_first(result, "documents"),
        query_first(result, "metadatas"),
    )


def text_details(items):
    return "\n".join(
        f"{item['rank']}. {item['heading']} | pages {item['pages']} | {item['reason']} | {item['preview']}"
        for item in items[:TEXT_TOP_DEBUG]
    )


def build_summary(rows):
    g1_text = summarize_rank(rows, "G1 텍스트 정답 순위", "G1 텍스트 평가")
    g2_text = summarize_rank(rows, "G2 텍스트 정답 순위", "G2 텍스트 평가")
    g3_text = summarize_rank(rows, "G3 텍스트 정답 순위", "G3 텍스트 평가")
    g3_image = summarize_rank(rows, "G3 이미지 정답 순위", "G3 이미지 평가")
    g4_text = summarize_rank(rows, "G4 텍스트 정답 순위", "G4 텍스트 평가")
    g4_image = summarize_rank(rows, "G4 이미지 정답 순위", "G4 이미지 평가")

    return {
        "G1": {
            "text": g1_text,
            "image": None,
            "both5": None,
            "both10": None,
        },
        "G2": {
            "text": g2_text,
            "image": None,
            "both5": None,
            "both10": None,
        },
        "G3": {
            "text": g3_text,
            "image": g3_image,
            "both5": both_at(rows, "G3 텍스트 정답 순위", "G3 이미지 정답 순위", 5),
            "both10": both_at(rows, "G3 텍스트 정답 순위", "G3 이미지 정답 순위", 10),
        },
        "G4": {
            "text": g4_text,
            "image": g4_image,
            "both5": both_at(rows, "G4 텍스트 정답 순위", "G4 이미지 정답 순위", 5),
            "both10": both_at(rows, "G4 텍스트 정답 순위", "G4 이미지 정답 순위", 10),
        },
    }


def summary_rows(summary):
    rows = []
    for group_id in ["G1", "G2", "G3", "G4"]:
        group = summary[group_id]
        image = group["image"]
        rows.append(
            {
                "비교군": group_id,
                "설명": GROUPS[group_id],
                "Text Recall@1": percent(group["text"]["recall_at_1"]),
                "Text Recall@5": percent(group["text"]["recall_at_5"]),
                "Text Recall@10": percent(group["text"]["recall_at_10"]),
                "Text MRR": score(group["text"]["mrr"]),
                "Image Recall@1": percent(image["recall_at_1"]) if image else "-",
                "Image Recall@5": percent(image["recall_at_5"]) if image else "-",
                "Image Recall@10": percent(image["recall_at_10"]) if image else "-",
                "Image MRR": score(image["mrr"]) if image else "-",
                "Both@5": percent(group["both5"]) if group["both5"] is not None else "-",
                "Both@10": percent(group["both10"]) if group["both10"] is not None else "-",
            }
        )
    return rows


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean_csv_rows(rows))


def write_xlsx(path, fields, rows, sheet_name):
    table = [fields] + [[row.get(field, "") for field in fields] for row in rows]
    write_workbook(table, path, sheet_name)


def write_report(summary):
    rows = summary_rows(summary)
    lines = [
        "# G1/G2/G3/G4 검색 성능 비교 결과",
        "",
        "## 비교군 정의",
        "",
        "| 구분 | 비교군 | 설명 |",
        "|---|---|---|",
        "| G1 | 키워드 기반 단순 검색 | 질문과 매뉴얼 chunk의 단어 일치도를 사용한 baseline |",
        "| G2 | 텍스트 기반 RAG | BGE-M3 텍스트 임베딩으로 텍스트 chunk만 검색 |",
        "| G3 | 멀티모달 RAG | 텍스트 검색, 이미지 전용 검색, page proximity, 텍스트-이미지 매핑 점수 사용 |",
        "| G4 | 상황 인지형 멀티모달 RAG | 질문에서 실습 단계를 추정한 뒤 G3 후보를 context map 기반으로 재순위화 |",
        "",
        "## 전체 비교표",
        "",
        "| 비교군 | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['비교군']} {row['설명']} | {row['Text Recall@1']} | {row['Text Recall@5']} | "
            f"{row['Text Recall@10']} | {row['Text MRR']} | {row['Image Recall@1']} | "
            f"{row['Image Recall@5']} | {row['Image Recall@10']} | {row['Image MRR']} | "
            f"{row['Both@5']} | {row['Both@10']} |"
        )

    g3 = summary["G3"]
    g4 = summary["G4"]
    lines.extend(
        [
            "",
            "## 해석",
            "",
            "- G1/G2는 이미지 검색을 수행하지 않기 때문에 Image Recall과 Both 지표는 산출하지 않았다.",
            "- G2와 G3의 텍스트 검색 경로는 동일한 BGE-M3 텍스트 컬렉션을 사용하므로 텍스트 성능은 같은 기준선으로 해석한다.",
            "- G3는 이미지/도식 후보를 추가해 멀티모달 검색 성능을 확인하는 비교군이다.",
            "- G4는 질문에서 실습 단계를 추정한 뒤, 실습 단계 문맥을 이용해 이미지 후보를 재순위화한 비교군이다.",
            f"- G4는 G3 대비 Image Recall@5가 {percent(g3['image']['recall_at_5'])}에서 {percent(g4['image']['recall_at_5'])}로, Image MRR이 {score(g3['image']['mrr'])}에서 {score(g4['image']['mrr'])}로 개선되었다.",
            "",
            "## 산출 파일",
            "",
            f"- `SCIE용/data/{DETAIL_OUTPUT_PATH.name}`",
            f"- `SCIE용/excel/{EXCEL_OUTPUT_PATH.name}`",
            f"- `SCIE용/data/{SUMMARY_CSV_PATH.name}`",
            f"- `SCIE용/excel/{SUMMARY_XLSX_PATH.name}`",
        ]
    )
    REPORT_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_model_cache()
    questions = read_csv_dicts(QUESTION_SET_PATH)
    g3_rows = {row["질문 번호"]: row for row in read_csv_dicts(G3_DETAIL_PATH)}
    g4_rows = {row["질문 번호"]: row for row in read_csv_dicts(G4_DETAIL_PATH)}

    keyword_docs, document_frequency = load_text_chunks()
    embedder = SentenceTransformer(BGE_M3_MODEL_ID, local_files_only=True)
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection = client.get_collection(name=TEXT_COLLECTION_NAME)

    rows = []
    for idx, question in enumerate(questions, start=1):
        g1_ids, g1_docs, g1_metas = keyword_search(
            question["질문"],
            keyword_docs,
            document_frequency,
            limit=TEXT_TOP_K,
        )
        g1_rank, g1_grade, g1_reason, g1_details = text_rank(
            expected_answer=question["정답 텍스트"],
            expected_page=question["페이지"],
            ids=g1_ids,
            docs=g1_docs,
            metas=g1_metas,
            embedder=embedder,
            text_collection=text_collection,
        )

        g2_ids, g2_docs, g2_metas = text_embedding_search(question["질문"], embedder, text_collection, limit=TEXT_TOP_K)
        g2_rank, g2_grade, g2_reason, g2_details = text_rank(
            expected_answer=question["정답 텍스트"],
            expected_page=question["페이지"],
            ids=g2_ids,
            docs=g2_docs,
            metas=g2_metas,
            embedder=embedder,
            text_collection=text_collection,
        )

        g3 = g3_rows.get(question["질문 번호"], {})
        g4 = g4_rows.get(question["질문 번호"], {})
        row = {
            "질문 번호": question["질문 번호"],
            "구분": question["구분"],
            "질문": question["질문"],
            "실습 단계": question["실습 단계"],
            "질문 유형": question["질문 유형"],
            "정답 텍스트": question["정답 텍스트"],
            "정답 이미지": question["정답 이미지"],
            "G1 텍스트 정답 순위": g1_rank,
            "G1 텍스트 평가": g1_grade,
            "G1 텍스트 평가 근거": g1_reason,
            "G1 검색 텍스트 Top-10": text_details(g1_details),
            "G2 텍스트 정답 순위": g2_rank,
            "G2 텍스트 평가": g2_grade,
            "G2 텍스트 평가 근거": g2_reason,
            "G2 검색 텍스트 Top-10": text_details(g2_details),
            "G3 텍스트 정답 순위": g3.get("텍스트 정답 순위", ""),
            "G3 텍스트 평가": g3.get("텍스트 평가", ""),
            "G3 이미지 정답 순위": g3.get("이미지 정답 순위", ""),
            "G3 이미지 평가": g3.get("이미지 평가", ""),
            "G4 텍스트 정답 순위": g4.get("G4 텍스트 정답 순위", ""),
            "G4 텍스트 평가": g4.get("G4 텍스트 평가", ""),
            "G4 이미지 정답 순위": g4.get("G4 이미지 정답 순위", ""),
            "G4 이미지 평가": g4.get("G4 이미지 평가", ""),
        }
        rows.append(row)
        print(
            f"[{idx}/{len(questions)}] {question['질문 번호']} "
            f"G1 text={g1_rank or '-'}:{g1_grade} "
            f"G2 text={g2_rank or '-'}:{g2_grade} "
            f"G3 image={row['G3 이미지 정답 순위'] or '-'}:{row['G3 이미지 평가'] or '-'} "
            f"G4 image={row['G4 이미지 정답 순위'] or '-'}:{row['G4 이미지 평가'] or '-'}",
            flush=True,
        )

    summary = build_summary(rows)
    summary_table = summary_rows(summary)

    write_csv(DETAIL_OUTPUT_PATH, DETAIL_FIELDS, rows)
    write_xlsx(EXCEL_OUTPUT_PATH, EXCEL_FIELDS, rows, "G1-G4 상세 평가")
    write_csv(SUMMARY_CSV_PATH, SUMMARY_FIELDS, summary_table)
    write_xlsx(SUMMARY_XLSX_PATH, SUMMARY_FIELDS, summary_table, "G1-G4 요약")
    write_report(summary)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"detail_excel: {EXCEL_OUTPUT_PATH}")
    print(f"summary: {SUMMARY_CSV_PATH}")
    print(f"summary_excel: {SUMMARY_XLSX_PATH}")
    print(f"report: {REPORT_OUTPUT_PATH}")
    for group_id in ["G1", "G2", "G3", "G4"]:
        group = summary[group_id]
        text = group["text"]
        image = group["image"]
        print(
            f"{group_id} text: "
            f"R@1={text['recall_at_1']:.3f} R@5={text['recall_at_5']:.3f} "
            f"R@10={text['recall_at_10']:.3f} MRR={text['mrr']:.3f}"
        )
        if image:
            print(
                f"{group_id} image: "
                f"R@1={image['recall_at_1']:.3f} R@5={image['recall_at_5']:.3f} "
                f"R@10={image['recall_at_10']:.3f} MRR={image['mrr']:.3f}"
            )


if __name__ == "__main__":
    main()
