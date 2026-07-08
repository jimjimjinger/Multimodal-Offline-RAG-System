import argparse
import csv
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import chromadb
import requests
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
    VECTOR_DB_DIR,
    configure_model_cache,
)
from rag_search import (  # noqa: E402
    ANSWER_TOP_K,
    IMAGE_COLLECTION_TOP_K,
    IMAGE_RESULTS_LIMIT,
    IMAGE_TEXT_TOP_K,
    open_rag_collections,
    retrieve_multimodal,
)
from stage_classifier import build_stage_profiles, classify_stage, encode_stage_profiles  # noqa: E402


TEMPLATE_PATH = SCIE_DATA_DIR / "17_response_quality_eval_template.csv"
RETRIEVAL_RESULT_PATH = SCIE_DATA_DIR / "15_g1_g2_g3_g4_retrieval_results.csv"

OUTPUT_CSV_PATH = SCIE_DATA_DIR / "22_response_quality_eval_results.csv"
OUTPUT_XLSX_PATH = SCIE_EXCEL_DIR / "22_response_quality_eval_results.xlsx"
SUMMARY_CSV_PATH = SCIE_DATA_DIR / "22_response_quality_eval_summary.csv"
SUMMARY_XLSX_PATH = SCIE_EXCEL_DIR / "22_response_quality_eval_summary.xlsx"
REPORT_PATH = SCIE_DIR / "22_response_quality_eval_results.md"

FIELDNAMES = [
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

GROUP_RANK_FIELDS = {
    "G2": ("G2 텍스트 정답 순위", ""),
    "G3": ("G3 텍스트 정답 순위", "G3 이미지 정답 순위"),
    "G4": ("G4 텍스트 정답 순위", "G4 이미지 정답 순위"),
}

TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
KOREAN_RE = re.compile(r"[가-힣]")
TECH_RE = re.compile(r"[A-Za-z0-9/+_.:-]")

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
    "확인",
    "입력",
    "출력",
    "무엇",
    "어떻게",
    "로봇",
    "시스템",
    "제어기",
    "컨트롤러",
    "두산로보틱스",
}

ERROR_MARKERS = [
    "Ollama 연동 실패",
    "응답 형식 오류",
    "시간이 너무 오래",
    "manual evidence is insufficient",
    "매뉴얼 근거가 부족",
    "근거가 부족",
]


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_dicts(path, rows, fieldnames=FIELDNAMES):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path, rows, fieldnames=FIELDNAMES, sheet_name="응답 품질 평가"):
    table = [fieldnames] + [[row.get(field, "") for field in fieldnames] for row in rows]
    write_workbook(table, path, sheet_name)


def normalize(value):
    return str(value or "").strip()


def tokens(value):
    result = []
    for token in TOKEN_RE.findall(normalize(value).lower()):
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        result.append(token)
    return result


def to_int(value):
    text = normalize(value)
    if not text or text == "-":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def row_key(row):
    return (row["질문 번호"], row["비교군"], row["모델"])


def load_base_rows(force=False):
    if OUTPUT_CSV_PATH.exists() and not force:
        rows = read_csv_dicts(OUTPUT_CSV_PATH)
    else:
        rows = read_csv_dicts(TEMPLATE_PATH)
    return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]


def enrich_ranks(rows):
    if not RETRIEVAL_RESULT_PATH.exists():
        return rows

    retrieval_by_question = {
        row["질문 번호"]: row for row in read_csv_dicts(RETRIEVAL_RESULT_PATH)
    }
    for row in rows:
        retrieval = retrieval_by_question.get(row["질문 번호"], {})
        text_field, image_field = GROUP_RANK_FIELDS.get(row["비교군"], ("", ""))
        row["검색 텍스트 순위"] = retrieval.get(text_field, "")
        row["검색 이미지 순위"] = retrieval.get(image_field, "") if image_field else ""
    return rows


def make_prompt(question, context):
    return f"""
You are a Korean technical support expert for Doosan Robotics collaborative robots.
You must answer only in Korean.
Do not answer in Chinese, English, Japanese, or Russian.
Use only the provided manual context.
If the context does not contain enough evidence, say that the manual evidence is insufficient.
Do not invent facts.

[매뉴얼 내용]
{context}

[질문]
{question}

[한국어 답변]
"""


def generate_answer(model_id, question, context, timeout=180):
    payload = {
        "model": model_id,
        "stream": False,
        "prompt": make_prompt(question, context),
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }
    try:
        response = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return normalize(data.get("response", f"Ollama 응답 형식 오류: {data}"))
    except requests.exceptions.Timeout:
        return f"{model_id}가 답변을 생성하는 데 시간이 너무 오래 걸립니다."
    except Exception as exc:
        return f"Ollama 연동 실패: {exc}"


def check_ollama():
    try:
        response = requests.get("http://127.0.0.1:11434/api/version", timeout=5)
        response.raise_for_status()
        return True, response.text
    except Exception as exc:
        return False, str(exc)


def build_retriever():
    configure_model_cache()
    embedder = SentenceTransformer("BAAI/bge-m3")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)
    stage_profiles = build_stage_profiles(STAGE_CONTEXT_MAP_MANUAL_PATH)
    stage_profile_embeddings = encode_stage_profiles(embedder, stage_profiles)
    return embedder, text_collection, image_collection, stage_profiles, stage_profile_embeddings


def retrieval_for_row(row, resources, cache):
    key = (row["질문 번호"], row["비교군"])
    if key in cache:
        return cache[key]

    embedder, text_collection, image_collection, stage_profiles, stage_profile_embeddings = resources
    group = row["비교군"]
    classification = None
    stage_label = None
    if group == "G4":
        classification = classify_stage(
            question=row["질문"],
            embedder=embedder,
            profiles=stage_profiles,
            profile_embeddings=stage_profile_embeddings,
            top_k=5,
        )
        stage_label = classification["stage_label"]

    active_image_collection = image_collection if group in {"G3", "G4"} else None

    retrieval = retrieve_multimodal(
        question=row["질문"],
        embedder=embedder,
        text_collection=text_collection,
        image_collection=active_image_collection,
        answer_top_k=ANSWER_TOP_K,
        image_text_top_k=IMAGE_TEXT_TOP_K,
        image_collection_top_k=IMAGE_COLLECTION_TOP_K,
        image_results_limit=IMAGE_RESULTS_LIMIT,
        stage_label=stage_label,
        stage_context_map_path=STAGE_CONTEXT_MAP_MANUAL_PATH if stage_label else None,
    )
    retrieval["stage_classification"] = classification
    cache[key] = retrieval
    return retrieval


def overlap_ratio(reference, answer):
    ref_tokens = set(tokens(reference))
    if not ref_tokens:
        return 0.0, []
    answer_tokens = set(tokens(answer))
    matched = sorted(ref_tokens & answer_tokens)
    return len(matched) / len(ref_tokens), matched


def has_error(answer):
    answer_lower = answer.lower()
    return any(marker.lower() in answer_lower for marker in ERROR_MARKERS)


def score_accuracy(reference, answer):
    if has_error(answer):
        return 1, 0.0, [], 0.0

    reference_text = normalize(reference)
    answer_text = normalize(answer)
    ratio, matched = overlap_ratio(reference_text, answer_text)

    if reference_text and reference_text in answer_text:
        return 5, ratio, matched, 0.0
    if ratio >= 0.75:
        return 5, ratio, matched, 0.0
    if ratio >= 0.5:
        return 4, ratio, matched, 0.0
    if ratio >= 0.25:
        return 3, ratio, matched, 0.0
    if ratio > 0:
        return 2, ratio, matched, 0.0
    return 1, ratio, matched, 0.0


def cosine_similarity(vec_a, vec_b):
    numerator = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if not norm_a or not norm_b:
        return 0.0
    return numerator / (norm_a * norm_b)


def semantic_similarity(embedder, reference, answer):
    if embedder is None or not normalize(reference) or not normalize(answer) or has_error(answer):
        return 0.0
    embeddings = embedder.encode([reference, answer])
    return float(cosine_similarity(embeddings[0], embeddings[1]))


def semantic_accuracy_score(similarity):
    if similarity >= 0.82:
        return 5
    if similarity >= 0.72:
        return 4
    if similarity >= 0.60:
        return 3
    if similarity >= 0.48:
        return 2
    return 1


def score_specificity(answer):
    if has_error(answer):
        return 1
    length = len(answer)
    tech_hits = len(TECH_RE.findall(answer))
    if length >= 180 and tech_hits >= 8:
        return 5
    if length >= 100 and tech_hits >= 4:
        return 4
    if length >= 50:
        return 3
    if length >= 20:
        return 2
    return 1


def score_stage_fit(row, accuracy_score):
    if has_error(row["모델 답변"]):
        return 1

    text_rank = to_int(row.get("검색 텍스트 순위"))
    stage_terms = set(tokens(row.get("실습 단계", "")))
    answer_terms = set(tokens(row.get("모델 답변", "")))
    stage_overlap = bool(stage_terms & answer_terms)

    if text_rank == 1 and accuracy_score >= 4:
        return 5
    if text_rank is not None and text_rank <= 5 and accuracy_score >= 4:
        return 5 if stage_overlap else 4
    if text_rank is not None and text_rank <= 10 and accuracy_score >= 3:
        return 4
    if accuracy_score >= 3:
        return 3
    if accuracy_score == 2:
        return 2
    return 1


def score_safety(row, accuracy_score):
    answer = row.get("모델 답변", "")
    if has_error(answer):
        return 1
    question_type = row.get("질문 유형", "")
    safety_question = "안전" in question_type or "안전" in row.get("실습 단계", "") or "위험" in row.get("질문", "")
    caution_terms = {"주의", "위험", "금지", "안전", "화재", "고장", "비상", "정지", "접지", "차단기"}
    answer_terms = set(tokens(answer))

    if accuracy_score <= 1:
        return 2
    if safety_question:
        if answer_terms & caution_terms:
            return 5 if accuracy_score >= 4 else 4
        return 3
    return 5 if accuracy_score >= 3 else 3


def score_readability(answer):
    if has_error(answer):
        return 1
    if not answer:
        return 1
    korean_count = len(KOREAN_RE.findall(answer))
    ratio = korean_count / max(1, len(answer))
    if ratio < 0.15:
        return 2
    if len(answer) > 1200:
        return 3
    if len(answer) >= 80:
        return 5
    if len(answer) >= 40:
        return 4
    if len(answer) >= 20:
        return 3
    return 2


def final_label(avg):
    if avg >= 4.0:
        return "O"
    if avg >= 3.0:
        return "△"
    return "X"


def evaluate_row(row, embedder=None):
    lexical_accuracy, ratio, matched, _ = score_accuracy(row["정답 텍스트"], row["모델 답변"])
    similarity = semantic_similarity(embedder, row["정답 텍스트"], row["모델 답변"])
    accuracy = max(lexical_accuracy, semantic_accuracy_score(similarity))
    specificity = score_specificity(row["모델 답변"])
    stage_fit = score_stage_fit(row, accuracy)
    safety = score_safety(row, accuracy)
    readability = score_readability(row["모델 답변"])
    avg = round((accuracy + specificity + stage_fit + safety + readability) / 5, 2)

    row["정확성(1-5)"] = str(accuracy)
    row["구체성(1-5)"] = str(specificity)
    row["실습 단계 적합성(1-5)"] = str(stage_fit)
    row["안전성(1-5)"] = str(safety)
    row["이해 용이성(1-5)"] = str(readability)
    row["평균 점수"] = f"{avg:.2f}"
    row["최종 판정(O/△/X)"] = final_label(avg)
    row["평가 메모"] = (
        "자동 1차 평가"
        f"; 정답키워드일치율={ratio:.2f}"
        f"; 의미유사도={similarity:.2f}"
        f"; 일치키워드={','.join(matched[:8])}"
        f"; 텍스트순위={row.get('검색 텍스트 순위', '')}"
        f"; 이미지순위={row.get('검색 이미지 순위', '')}"
    )
    return row


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if not row.get("평균 점수"):
            continue
        groups[(row["비교군"], row["비교군 설명"], row["모델"])].append(row)

    summary_rows = []
    for (group_id, group_label, model), items in sorted(groups.items()):
        scores = [float(item["평균 점수"]) for item in items]
        judgments = defaultdict(int)
        for item in items:
            judgments[item["최종 판정(O/△/X)"]] += 1
        summary_rows.append(
            {
                "비교군": group_id,
                "비교군 설명": group_label,
                "모델": model,
                "평가 수": str(len(items)),
                "평균 점수": f"{sum(scores) / len(scores):.2f}",
                "O": str(judgments["O"]),
                "△": str(judgments["△"]),
                "X": str(judgments["X"]),
            }
        )

    return summary_rows


def write_summary(summary_rows):
    fields = ["비교군", "비교군 설명", "모델", "평가 수", "평균 점수", "O", "△", "X"]
    write_csv_dicts(SUMMARY_CSV_PATH, summary_rows, fields)
    write_xlsx(SUMMARY_XLSX_PATH, summary_rows, fields, "응답 품질 요약")


def write_report(rows, summary_rows):
    complete_count = sum(1 for row in rows if row.get("평균 점수"))
    total_count = len(rows)
    lines = [
        "# 응답 품질 평가 결과",
        "",
        "## 평가 성격",
        "",
        "이 결과는 5개 항목 rubric을 이용한 자동 1차 평가이다. 논문 최종본에서는 전문가 또는 연구자의 수동 검토 결과로 보완하는 것이 바람직하다.",
        "",
        "## 진행 현황",
        "",
        f"- 전체 평가 대상: {total_count}개",
        f"- 평가 완료: {complete_count}개",
        f"- 평가 미완료: {total_count - complete_count}개",
        "",
        "## 비교군/모델별 요약",
        "",
        "| 비교군 | 설명 | 모델 | 평가 수 | 평균 점수 | O | △ | X |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['비교군']} | {row['비교군 설명']} | {row['모델']} | "
            f"{row['평가 수']} | {row['평균 점수']} | {row['O']} | {row['△']} | {row['X']} |"
        )

    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            f"- `{OUTPUT_CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{OUTPUT_XLSX_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{SUMMARY_CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{SUMMARY_XLSX_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="maximum number of unanswered rows to process; 0 means all")
    parser.add_argument("--groups", nargs="*", default=["G2", "G3", "G4"])
    parser.add_argument("--models", nargs="*", default=["Qwen", "Gemma", "Llama"])
    parser.add_argument("--force", action="store_true", help="start from the template and overwrite existing results")
    parser.add_argument(
        "--regenerate-existing",
        action="store_true",
        help="regenerate answers for selected groups/models even when an answer already exists",
    )
    parser.add_argument("--rescore-only", action="store_true", help="do not generate answers; rescore existing answers")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = enrich_ranks(load_base_rows(force=args.force))

    should_generate = not args.rescore_only
    resources = None
    scoring_embedder = None
    retrieval_cache = {}
    if should_generate:
        ok, info = check_ollama()
        if not ok:
            raise SystemExit(f"Ollama server is not available: {info}")
        resources = build_retriever()
        scoring_embedder = resources[0]
    else:
        configure_model_cache()
        scoring_embedder = SentenceTransformer("BAAI/bge-m3")

    processed = 0
    start = time.time()
    for index, row in enumerate(rows, start=1):
        if row["비교군"] not in args.groups or row["모델"] not in args.models:
            continue

        if should_generate and args.regenerate_existing:
            row["모델 답변"] = ""

        answer_exists = bool(normalize(row.get("모델 답변")))
        if should_generate and not answer_exists:
            retrieval = retrieval_for_row(row, resources, retrieval_cache)
            row["모델 답변"] = generate_answer(row["모델 ID"], row["질문"], retrieval["context"])

        if normalize(row.get("모델 답변")):
            evaluate_row(row, embedder=scoring_embedder)

        if should_generate and not answer_exists:
            processed += 1
            write_csv_dicts(OUTPUT_CSV_PATH, rows)
            elapsed = time.time() - start
            print(
                f"[{processed}] row={index}/{len(rows)} "
                f"{row['질문 번호']} {row['비교군']} {row['모델']} "
                f"avg={row['평균 점수']} elapsed={elapsed:.1f}s",
                flush=True,
            )
            if args.limit and processed >= args.limit:
                break

    write_csv_dicts(OUTPUT_CSV_PATH, rows)
    write_xlsx(OUTPUT_XLSX_PATH, rows)
    summary_rows = summarize(rows)
    write_summary(summary_rows)
    write_report(rows, summary_rows)

    print(f"created: {OUTPUT_CSV_PATH}")
    print(f"created: {OUTPUT_XLSX_PATH}")
    print(f"created: {SUMMARY_CSV_PATH}")
    print(f"created: {SUMMARY_XLSX_PATH}")
    print(f"created: {REPORT_PATH}")


if __name__ == "__main__":
    main()
