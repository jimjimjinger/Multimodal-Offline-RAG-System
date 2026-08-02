import csv
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import chromadb
import requests
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import (  # noqa: E402
    EVALUATION_DATA_DIR,
    VECTOR_DB_DIR,
    configure_model_cache,
)
from rag_search import open_rag_collections, retrieve_multimodal  # noqa: E402


TESTSET_PATH = EVALUATION_DATA_DIR / "testset.xlsx"
RAW_OUTPUT_PATH = EVALUATION_DATA_DIR / "model_eval_raw.csv"
SUMMARY_OUTPUT_PATH = EVALUATION_DATA_DIR / "model_eval_summary.csv"
IMAGE_O_LIMIT = 5
IMAGE_PARTIAL_LIMIT = 10

MODELS = [
    ("qwen", "qwen2.5:7b", "Qwen 2.5 7B Q4"),
    ("gemma", "gemma2:9b", "Gemma 2 9B Q4"),
    ("llama", "llama3.1:8b", "Llama 3.1 8B Q4"),
]

RAW_FIELDS = [
    "qid",
    "model_key",
    "model_id",
    "model_label",
    "question",
    "expected_answer",
    "expected_page",
    "expected_image",
    "answer",
    "retrieved_images",
    "retrieved_headings",
    "image_grade",
    "text_grade",
    "final_grade",
    "matched_patterns",
    "total_patterns",
    "elapsed_sec",
]

TEXT_PATTERNS = {
    "Q01": [r"화재", r"컨트롤러.*(고장|손상)|컨트롤러", r"고장|손상"],
    "Q02": [r"접지", r"누전\s*차단기|누전차단기"],
    "Q03": [r"m\s*8|M\s*8", r"20\s*n\s*m|20\s*Nm|20\s*뉴턴"],
    "Q04": [r"tbsft", r"\bem\b|em\s*단자"],
    "Q05": [r"5\s*번|핀\s*5|pin\s*5", r"8\s*번|핀\s*8|pin\s*8"],
    "Q06": [r"상단|위쪽", r"우측|오른쪽"],
    "Q07": [r"cockpit|콕핏"],
    "Q08": [r"pull\s*-?\s*up|풀\s*-?\s*업", r"24\s*v|12\s*v|vcc"],
    "Q09": [r"pr\s*단자|\bpr\b|보호\s*정지", r"tbsft"],
    "Q10": [r"status|상태", r"i/o\s*overview|io\s*overview|I/O\s*Overview"],
    "Q11": [r"y\s*축|y-axis|y축", r"z\s*축|z-axis|z축", r"회전|각도"],
    "Q12": [r"backdrive|백\s*드라이브|백드라이브"],
    "Q13": [r"전원\s*버튼|power", r"4\s*초"],
    "Q14": [r"속도|속력|각도", r"제한|위반", r"에러|오류|정지"],
    "Q15": [r"logs?|로그"],
    "Q16": [r"120\s*mm|120\s*밀리"],
    "Q17": [r"4\s*번|핀\s*4|pin\s*4", r"6\s*번|핀\s*6|pin\s*6"],
    "Q18": [r"협착|crushing"],
    "Q19": [r"태스크\s*모션|task\s*motion"],
    "Q20": [r"z\s*값|z\s*축|z\s*항목|z"],
    "Q21": [
        r"구|sphere",
        r"원기둥|cylinder",
        r"직육면체|cuboid",
        r"다면상자|multi\s*-?\s*plane|기울어진|tilted",
    ],
    "Q22": [r"task\s*editor|태스크\s*에디터"],
    "Q23": [r"header|헤더"],
    "Q24": [r"movel|move\s*l"],
    "Q25": [r"movej|move\s*j"],
    "Q26": [r"\.dm|\bdm\b"],
    "Q27": [r"데이터\s*베이스|데이터베이스|database", r"로그", r"워크셀|workcell", r"태스크|task"],
    "Q28": [r"그로밋|grommet"],
    "Q29": [r"z\s*축|z축"],
    "Q30": [r"극성", r"반대|역|잘못"],
    "Q31": [r"usb", r"로그|백업|내보내기|가져오기|태스크"],
    "Q32": [r"home\s*position|홈\s*포지션|홈포지션"],
    "Q33": [r"admin"],
    "Q34": [r"패키징|packaging"],
    "Q35": [r"vcc\s*-?\s*vio|vcc-vio", r"gnd\s*-?\s*gio|gnd-gio"],
    "Q36": [r"기준점", r"x\s*축", r"xy\s*평면|xy평면"],
    "Q37": [r"set_external_force_reset"],
    "Q38": [r"slot\s*#?\s*1|slot#1|1\s*번\s*slot|slot\s*번호\s*1|1\s*번"],
}


def col_to_idx(cell_ref):
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + ord(ch.upper()) - ord("A") + 1
    return idx - 1


def read_testset(path):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))

        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                idx = col_to_idx(cell.attrib.get("r", "A1"))
                while len(values) <= idx:
                    values.append("")
                value_node = cell.find("a:v", ns)
                value = "" if value_node is None else value_node.text or ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[idx] = value
            rows.append(values)

    records = []
    for row in rows[1:]:
        row = row + [""] * (5 - len(row))
        records.append(
            {
                "qid": row[0],
                "question": row[1],
                "expected_answer": row[2],
                "expected_page": row[3],
                "expected_image": row[4],
            }
        )
    return records


def load_done(path):
    if not path.exists():
        return set()
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return {(row["qid"], row["model_key"]) for row in csv.DictReader(f)}


def append_raw(row):
    exists = RAW_OUTPUT_PATH.exists()
    with RAW_OUTPUT_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def make_context(retrieved_docs, retrieved_metas):
    combined_context = ""
    for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas), start=1):
        heading = meta.get("heading", "제목 없음")
        pages = meta.get("pages", "페이지 정보 없음")
        combined_context += f"[관련도 {i}순위 자료 | 출처: {heading} (페이지 {pages})]\n{doc}\n\n"
    return combined_context


def collect_images(retrieved_metas):
    collected = []
    seen = set()
    for rank, meta in enumerate(retrieved_metas, start=1):
        try:
            paths = json.loads(meta.get("linked_images", "[]"))
        except json.JSONDecodeError:
            paths = []

        for image_path in paths:
            resolved = resolve_image_path(image_path)
            key = resolved.name
            if key in seen or not resolved.exists():
                continue
            seen.add(key)
            collected.append(
                {
                    "rank": rank,
                    "name": key,
                    "path": str(resolved),
                    "heading": meta.get("heading", "제목 없음"),
                    "pages": meta.get("pages", "페이지 정보 없음"),
                }
            )
    return collected


def generate_answer(model_id, question, context):
    prompt = f"""
You are a Korean technical support expert for Doosan Robotics collaborative robots.
You must answer only in Korean.
Do not answer in Chinese, English, Japanese, or Russian.
Use only the provided manual context.
If the context does not contain enough evidence, say that the manual evidence is insufficient.
Do not invent facts.
Answer concisely in one to three sentences.

[매뉴얼 내용]
{context}

[질문]
{question}

[한국어 답변]
"""
    payload = {
        "model": model_id,
        "stream": False,
        "prompt": prompt,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": 180,
        },
    }
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=240)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def text_grade(qid, answer):
    patterns = TEXT_PATTERNS.get(qid, [])
    if not patterns:
        return "△", 0, 0

    matched = 0
    for pattern in patterns:
        if re.search(pattern, answer, flags=re.IGNORECASE):
            matched += 1

    total = len(patterns)
    if matched == total:
        grade = "O"
    elif matched >= max(1, (total + 1) // 2):
        grade = "△"
    else:
        grade = "X"
    return grade, matched, total


def image_grade(expected_image, retrieved_images):
    for rank, image in enumerate(retrieved_images[:IMAGE_PARTIAL_LIMIT], start=1):
        if image.get("name") == expected_image:
            return "O" if rank <= IMAGE_O_LIMIT else "\u25b3"
    return "X"


def final_grade(text, image):
    if text == "O" and image == "O":
        return "O"
    if text == "X" and image == "X":
        return "X"
    return "△"


def write_summary(test_records):
    raw_rows = []
    if RAW_OUTPUT_PATH.exists():
        with RAW_OUTPUT_PATH.open("r", newline="", encoding="utf-8-sig") as f:
            raw_rows = list(csv.DictReader(f))

    by_key = {(r["qid"], r["model_key"]): r for r in raw_rows}
    fields = [
        "qid",
        "question",
        "expected_answer",
        "expected_image",
        "qwen",
        "gemma",
        "llama",
        "qwen_text",
        "qwen_image",
        "gemma_text",
        "gemma_image",
        "llama_text",
        "llama_image",
    ]

    with SUMMARY_OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in test_records:
            row = {
                "qid": record["qid"],
                "question": record["question"],
                "expected_answer": record["expected_answer"],
                "expected_image": record["expected_image"],
            }
            for model_key, _, _ in MODELS:
                raw = by_key.get((record["qid"], model_key), {})
                row[model_key] = raw.get("final_grade", "")
                row[f"{model_key}_text"] = raw.get("text_grade", "")
                row[f"{model_key}_image"] = raw.get("image_grade", "")
            writer.writerow(row)


def main():
    EVALUATION_DATA_DIR.mkdir(parents=True, exist_ok=True)
    test_records = read_testset(TESTSET_PATH)
    done = load_done(RAW_OUTPUT_PATH)

    configure_model_cache()
    embedder = SentenceTransformer("BAAI/bge-m3")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)

    retrieval_cache = {}
    for idx, record in enumerate(test_records, start=1):
        retrieval = retrieve_multimodal(
            question=record["question"],
            embedder=embedder,
            text_collection=text_collection,
            image_collection=image_collection,
        )
        retrieval_cache[record["qid"]] = {
            "context": retrieval["context"],
            "images": retrieval["images"],
            "headings": [
                {
                    "rank": i + 1,
                    "heading": meta.get("heading", ""),
                    "pages": meta.get("pages", ""),
                }
                for i, meta in enumerate(retrieval["answer_metas"])
            ],
        }
        print(f"[retrieval] {idx}/{len(test_records)} {record['qid']}", flush=True)

    total_tasks = len(test_records) * len(MODELS)
    completed = len(done)
    for model_key, model_id, model_label in MODELS:
        print(f"[model-start] {model_label} ({model_id})", flush=True)
        for record in test_records:
            if (record["qid"], model_key) in done:
                continue

            retrieval = retrieval_cache[record["qid"]]
            start = time.time()
            try:
                answer = generate_answer(model_id, record["question"], retrieval["context"])
            except Exception as exc:
                answer = f"ERROR: {exc}"

            image = image_grade(record["expected_image"], retrieval["images"])
            text, matched, total = text_grade(record["qid"], answer)
            final = final_grade(text, image)
            elapsed = round(time.time() - start, 2)

            append_raw(
                {
                    "qid": record["qid"],
                    "model_key": model_key,
                    "model_id": model_id,
                    "model_label": model_label,
                    "question": record["question"],
                    "expected_answer": record["expected_answer"],
                    "expected_page": record["expected_page"],
                    "expected_image": record["expected_image"],
                    "answer": answer,
                    "retrieved_images": json.dumps(retrieval["images"], ensure_ascii=False),
                    "retrieved_headings": json.dumps(retrieval["headings"], ensure_ascii=False),
                    "image_grade": image,
                    "text_grade": text,
                    "final_grade": final,
                    "matched_patterns": matched,
                    "total_patterns": total,
                    "elapsed_sec": elapsed,
                }
            )
            completed += 1
            print(
                f"[answer] {completed}/{total_tasks} {model_key} {record['qid']} "
                f"text={text} image={image} final={final} elapsed={elapsed}s",
                flush=True,
            )

    write_summary(test_records)
    print(f"[done] raw={RAW_OUTPUT_PATH}", flush=True)
    print(f"[done] summary={SUMMARY_OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
