import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import VECTOR_DB_DIR, configure_model_cache  # noqa: E402
from rag_search import (  # noqa: E402
    IMAGE_COLLECTION_TOP_K,
    IMAGE_RESULTS_LIMIT,
    IMAGE_TEXT_TOP_K,
    extract_pages,
    open_rag_collections,
    retrieve_multimodal,
)


TEXT_TOP_K = 10
IMAGE_O_LIMIT = 5
IMAGE_PARTIAL_LIMIT = 10
PARTIAL = "△"
SEMANTIC_TEXT_TOP_K = 20
SEMANTIC_TEXT_ACCEPT_RANK = 15


def find_scie_dir():
    return next(path for path in PROJECT_ROOT.iterdir() if path.is_dir() and path.name.startswith("SCIE"))


SCIE_DIR = find_scie_dir()
SCIE_DATA_DIR = SCIE_DIR / "data"
SCIE_EXCEL_DIR = SCIE_DIR / "excel"
QUESTION_SET_PATH = SCIE_DATA_DIR / "03_question_set_70.csv"
DETAIL_OUTPUT_PATH = SCIE_DATA_DIR / "07_pilot_retrieval_results.csv"
REPORT_OUTPUT_PATH = SCIE_DIR / "07_pilot_results.md"


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
}

KOREAN_SUFFIXES = (
    "입니다",
    "합니다",
    "하십시오",
    "하거나",
    "하며",
    "하고",
    "에서",
    "으로",
    "까지",
    "부터",
    "에게",
    "에는",
    "에는",
    "와",
    "과",
    "을",
    "를",
    "은",
    "는",
    "이",
    "가",
    "의",
    "에",
)


def read_questions():
    with QUESTION_SET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def strip_korean_suffix(token):
    stripped = token
    for suffix in KOREAN_SUFFIXES:
        if len(stripped) > len(suffix) + 1 and stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)]
            break
    return stripped


def keyword_terms(expected_answer):
    terms = []
    for token in re.findall(r"[0-9A-Za-z가-힣]+", normalize_text(expected_answer)):
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        terms.append(token)
        stripped = strip_korean_suffix(token)
        if stripped != token and len(stripped) >= 2 and stripped not in STOPWORDS:
            terms.append(stripped)

    unique_terms = []
    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)
    return unique_terms


def keyword_match_score(expected_answer, candidate_text):
    terms = keyword_terms(expected_answer)
    if not terms:
        return 0.0, [], terms

    text = normalize_text(candidate_text)
    matched = [term for term in terms if term in text]
    return len(matched) / len(terms), matched, terms


def expected_page_match(expected_page, meta):
    expected_pages = [int(value) for value in re.findall(r"\d+", str(expected_page or ""))]
    if not expected_pages:
        return False
    retrieved_pages = extract_pages(meta.get("pages"))
    return any(page in retrieved_pages for page in expected_pages)


def is_text_match(expected_answer, expected_page, doc, meta, semantic_rank):
    candidate_text = f"{meta.get('heading', '')} {meta.get('pages', '')} {doc}"
    page_match = expected_page_match(expected_page, meta)
    keyword_score, matched_terms, all_terms = keyword_match_score(expected_answer, candidate_text)
    needed_terms = max(1, (len(all_terms) + 2) // 3) if all_terms else 1
    keyword_match = len(matched_terms) >= needed_terms
    semantic_match = bool(semantic_rank and semantic_rank <= SEMANTIC_TEXT_ACCEPT_RANK)

    matched = page_match or keyword_match or semantic_match
    reasons = []
    if page_match:
        reasons.append("page")
    if keyword_match:
        reasons.append(f"keyword:{','.join(matched_terms[:6])}")
    if semantic_match:
        reasons.append(f"semantic_rank:{semantic_rank}")
    if not reasons:
        reasons.append(f"no_match keyword={keyword_score:.2f} semantic_rank={semantic_rank or '-'}")
    return matched, "; ".join(reasons), keyword_score


def semantic_answer_ids(expected_answer, embedder, text_collection):
    answer_embedding = embedder.encode(expected_answer).tolist()
    result = text_collection.query(query_embeddings=[answer_embedding], n_results=SEMANTIC_TEXT_TOP_K)
    ids = result.get("ids") or [[]]
    return ids[0] if ids else []


def text_rank(expected_answer, expected_page, ids, docs, metas, embedder, text_collection):
    if not docs:
        return "", "X", "", []

    semantic_ids = semantic_answer_ids(expected_answer, embedder, text_collection)
    semantic_rank_by_id = {doc_id: rank for rank, doc_id in enumerate(semantic_ids, start=1)}

    details = []
    matched_rank = ""
    matched_reason = ""
    for rank, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), start=1):
        semantic_rank = semantic_rank_by_id.get(doc_id)
        matched, reason, keyword_score = is_text_match(
            expected_answer=expected_answer,
            expected_page=expected_page,
            doc=doc,
            meta=meta,
            semantic_rank=semantic_rank,
        )
        pages = meta.get("pages", "")
        heading = meta.get("heading", "")
        details.append(
            {
                "rank": rank,
                "heading": heading,
                "pages": pages,
                "semantic_rank": semantic_rank,
                "keyword_score": round(keyword_score, 3),
                "matched": matched,
                "reason": reason,
                "preview": re.sub(r"\s+", " ", doc)[:180],
            }
        )
        if matched and not matched_rank:
            matched_rank = rank
            matched_reason = reason

    if matched_rank:
        grade = "O" if matched_rank <= 5 else PARTIAL
    else:
        grade = "X"
    return matched_rank, grade, matched_reason, details


def image_rank(expected_image, retrieved_images):
    for rank, image in enumerate(retrieved_images[:IMAGE_PARTIAL_LIMIT], start=1):
        if image.get("name") == expected_image:
            return rank, "O" if rank <= IMAGE_O_LIMIT else PARTIAL
    return "", "X"


def reciprocal_rank(rank):
    return 0.0 if not rank else 1.0 / int(rank)


def summarize_rank(rows, rank_key, grade_key):
    total = len(rows)
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
        "정답 텍스트",
        "텍스트 정답 순위",
        "텍스트 평가",
        "텍스트 평가 근거",
        "검색 텍스트 Top-10",
        "정답 이미지",
        "이미지 정답 순위",
        "이미지 평가",
        "검색 이미지 Top-10",
    ]
    with DETAIL_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(text_summary, image_summary, rows):
    both_top5 = sum(
        1
        for row in rows
        if row["텍스트 정답 순위"]
        and int(row["텍스트 정답 순위"]) <= 5
        and row["이미지 정답 순위"]
        and int(row["이미지 정답 순위"]) <= 5
    )
    both_top10 = sum(
        1
        for row in rows
        if row["텍스트 정답 순위"]
        and int(row["텍스트 정답 순위"]) <= 10
        and row["이미지 정답 순위"]
        and int(row["이미지 정답 순위"]) <= 10
    )

    lines = [
        "# 1차 파일럿 실험 결과",
        "",
        "## 실험 목적",
        "",
        "현재 구현된 G3 멀티모달 RAG가 70개 질의셋에서 정답 텍스트와 정답 이미지를 얼마나 잘 검색하는지 확인하였다.",
        "",
        "이번 파일럿은 G3 멀티모달 RAG를 대상으로 수행했으며, 텍스트 검색 성능과 이미지 검색 성능을 분리해 평가하였다.",
        "텍스트 평가는 정답 문장과 완전 일치만 보는 방식이 아니라, 정답 page 일치, 핵심 keyword 포함, 의미 유사도 중 하나가 충분하면 정답으로 인정하는 관대한 기준을 적용하였다.",
        "",
        "## 실험 조건",
        "",
        "| 항목 | 내용 |",
        "|---|---|",
        "| 평가 질의셋 | `SCIE용/data/03_question_set_70.csv` |",
        "| 질문 수 | 70개 |",
        "| 비교군 | G3 멀티모달 RAG |",
        "| 텍스트 임베딩 | BGE-M3 |",
        "| 텍스트 검색 평가 | 정답 텍스트의 page, 핵심 keyword, 의미 유사도 기준 |",
        "| 이미지 검색 평가 | 정답 이미지가 검색 이미지 Top-10 안에 포함되는지 확인 |",
        "",
        "## 텍스트 검색 성능",
        "",
        "| 지표 | 결과 |",
        "|---|---:|",
        f"| Text Recall@1 | {percent(text_summary['recall_at_1'])} |",
        f"| Text Recall@5 | {percent(text_summary['recall_at_5'])} |",
        f"| Text Recall@10 | {percent(text_summary['recall_at_10'])} |",
        f"| Text MRR | {text_summary['mrr']:.3f} |",
        "",
        "## 이미지 검색 성능",
        "",
        "| 지표 | 결과 |",
        "|---|---:|",
        f"| Image Recall@1 | {percent(image_summary['recall_at_1'])} |",
        f"| Image Recall@5 | {percent(image_summary['recall_at_5'])} |",
        f"| Image Recall@10 | {percent(image_summary['recall_at_10'])} |",
        f"| Image MRR | {image_summary['mrr']:.3f} |",
        "",
        "## O/△/X 요약",
        "",
        "| 평가 대상 | O | △ | X | 전체 |",
        "|---|---:|---:|---:|---:|",
        f"| 텍스트 | {text_summary['O']} | {text_summary[PARTIAL]} | {text_summary['X']} | {text_summary['total']} |",
        f"| 이미지 | {image_summary['O']} | {image_summary[PARTIAL]} | {image_summary['X']} | {image_summary['total']} |",
        "",
        "## 동시 검색 성공률",
        "",
        "| 지표 | 결과 |",
        "|---|---:|",
        f"| Text + Image Both@5 | {percent(both_top5 / len(rows))} |",
        f"| Text + Image Both@10 | {percent(both_top10 / len(rows))} |",
        "",
        "## 해석",
        "",
        "- Text Recall@k는 정답 텍스트의 핵심 내용이 검색 텍스트 Top-k 안에 포함되는지를 의미한다.",
        "- Image Recall@k는 정답 이미지가 검색 이미지 Top-k 안에 포함되는지를 의미한다.",
        "- 텍스트 검색은 page, keyword, 의미 유사도 중 하나가 충분하면 정답으로 인정했기 때문에, 엄격한 문장 일치 평가보다 관대한 기준이다.",
        "- 이미지 검색은 파일명 기준으로 정답 이미지가 Top-k 안에 포함되는지 확인했다.",
        "",
        "## 상세 결과 파일",
        "",
        "- `SCIE용/data/07_pilot_retrieval_results.csv`: 검색 텍스트 Top-10까지 포함한 전체 디버깅용 원본",
        "- `SCIE용/excel/07_pilot_retrieval_results.xlsx`: 교수님 보고용 요약 파일. 검색 텍스트 Top-10은 제외하고 핵심 평가 컬럼만 포함",
    ]

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
            answer_top_k=TEXT_TOP_K,
            image_text_top_k=IMAGE_TEXT_TOP_K,
            image_collection_top_k=IMAGE_COLLECTION_TOP_K,
            image_results_limit=IMAGE_RESULTS_LIMIT,
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

        rows.append(
            {
                "질문 번호": question["질문 번호"],
                "구분": question["구분"],
                "질문": question["질문"],
                "실습 단계": question["실습 단계"],
                "질문 유형": question["질문 유형"],
                "정답 텍스트": question["정답 텍스트"],
                "텍스트 정답 순위": t_rank,
                "텍스트 평가": t_grade,
                "텍스트 평가 근거": t_reason,
                "검색 텍스트 Top-10": "\n".join(
                    f"{item['rank']}. {item['heading']} | pages {item['pages']} | {item['reason']} | {item['preview']}"
                    for item in t_details
                ),
                "정답 이미지": question["정답 이미지"],
                "이미지 정답 순위": i_rank,
                "이미지 평가": i_grade,
                "검색 이미지 Top-10": "\n".join(
                    f"{i}. {image['name']}" for i, image in enumerate(retrieval["images"][:IMAGE_PARTIAL_LIMIT], start=1)
                ),
            }
        )
        print(
            f"[{idx}/{len(questions)}] {question['질문 번호']} "
            f"text={t_rank or '-'}:{t_grade} image={i_rank or '-'}:{i_grade}",
            flush=True,
        )

    text_summary = summarize_rank(rows, "텍스트 정답 순위", "텍스트 평가")
    image_summary = summarize_rank(rows, "이미지 정답 순위", "이미지 평가")
    write_detail(rows)
    write_report(text_summary, image_summary, rows)

    print(f"detail: {DETAIL_OUTPUT_PATH}")
    print(f"report: {REPORT_OUTPUT_PATH}")
    print(
        "text metrics: "
        f"R@1={text_summary['recall_at_1']:.3f} "
        f"R@5={text_summary['recall_at_5']:.3f} "
        f"R@10={text_summary['recall_at_10']:.3f} "
        f"MRR={text_summary['mrr']:.3f}"
    )
    print(
        "image metrics: "
        f"R@1={image_summary['recall_at_1']:.3f} "
        f"R@5={image_summary['recall_at_5']:.3f} "
        f"R@10={image_summary['recall_at_10']:.3f} "
        f"MRR={image_summary['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()
