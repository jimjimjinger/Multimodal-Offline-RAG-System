import chromadb
import requests
import streamlit as st
from PIL import Image
from sentence_transformers import SentenceTransformer

from paths import VECTOR_DB_DIR, configure_model_cache
from rag_search import (
    ANSWER_TOP_K,
    IMAGE_COLLECTION_TOP_K,
    IMAGE_RESULTS_LIMIT,
    IMAGE_TEXT_TOP_K,
    open_rag_collections,
    retrieve_multimodal,
)


@st.cache_resource
def load_resources():
    configure_model_cache()
    embedder = SentenceTransformer("BAAI/bge-m3")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    text_collection, image_collection = open_rag_collections(client)
    return embedder, text_collection, image_collection


def generate_answer(model_id, question, context):
    prompt = f"""
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

    payload = {
        "model": model_id,
        "stream": False,
        "prompt": prompt,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
        },
    }

    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        if "response" in data:
            return data["response"]
        return f"Ollama 응답 형식 오류: {data}"
    except requests.exceptions.Timeout:
        return f"{model_id}가 답변을 생성하는 데 시간이 너무 오래 걸립니다."
    except Exception as exc:
        return f"Ollama 연동 실패: {exc}"


def render_sidebar(model_id, model_label, image_collection):
    with st.sidebar:
        st.title("Intelligent Assistant")
        st.info(f"BGE-M3 + ChromaDB + {model_label}")
        st.write(f"**LLM:** {model_id}")
        st.write("**Answer search:** text Top-5")
        st.write(f"**Image search:** text Top-{IMAGE_TEXT_TOP_K} + image DB Top-{IMAGE_COLLECTION_TOP_K}")
        st.write(f"**Displayed images:** Top-{IMAGE_RESULTS_LIMIT}")
        st.write(f"**Image DB:** {'enabled' if image_collection is not None else 'not built'}")
        st.markdown("---")
        st.write("터미널에서 `powershell -ExecutionPolicy Bypass -File .\\start_ollama.ps1`가 실행 중이어야 합니다.")


def render_answer_sources(retrieved_docs, retrieved_metas):
    with st.expander("참조한 Top-5 매뉴얼 원문"):
        for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas), start=1):
            heading = meta.get("heading", "제목 없음")
            pages = meta.get("pages", "페이지 정보 없음")
            st.success(f"**[{i}순위] Section:** {heading} (Page {pages})")
            st.write(doc)
            st.divider()


def render_images(images):
    st.markdown("### 참조 도면 이미지")
    if not images:
        st.warning("검색 결과에서 연결된 도면 이미지를 찾을 수 없습니다.")
        return

    for image_info in images:
        image = Image.open(image_info["path"])
        caption = (
            f"[{image_info['rank']}순위 | score {image_info['score']:.3f}] "
            f"{image_info['name']} | {image_info['heading']} | Page {image_info['pages']}"
        )
        st.image(image, use_container_width=True, caption=caption)


def run_app(model_id, model_label, page_title):
    st.set_page_config(layout="wide", page_title=page_title)
    embedder, text_collection, image_collection = load_resources()
    render_sidebar(model_id, model_label, image_collection)

    st.header("두산로보틱스 지능형 Q&A 시스템")
    st.caption(
        f"{model_label} 기반 답변과 Top-{ANSWER_TOP_K} 텍스트 검색, "
        f"Top-{IMAGE_TEXT_TOP_K} 확장 이미지 검색 결과를 함께 제공합니다."
    )

    query = st.text_input("질문을 입력하세요", placeholder="예: 서보 온(Servo On) 절차를 알려줘")
    if not query:
        return

    retrieval = retrieve_multimodal(
        question=query,
        embedder=embedder,
        text_collection=text_collection,
        image_collection=image_collection,
        answer_top_k=ANSWER_TOP_K,
        image_text_top_k=IMAGE_TEXT_TOP_K,
        image_collection_top_k=IMAGE_COLLECTION_TOP_K,
        image_results_limit=IMAGE_RESULTS_LIMIT,
    )

    if not retrieval["answer_docs"]:
        st.error("매뉴얼에서 관련 정보를 찾지 못했습니다.")
        return

    with st.spinner(f"{model_id}가 Top-{ANSWER_TOP_K} 매뉴얼 문서를 종합 분석 중입니다..."):
        ai_answer = generate_answer(model_id, query, retrieval["context"])

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.markdown("### 로컬 LLM 답변")
        st.write(ai_answer)
        render_answer_sources(retrieval["answer_docs"], retrieval["answer_metas"])

    with col2:
        render_images(retrieval["images"])
