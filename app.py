import streamlit as st
import chromadb
import json
import os
import requests
from sentence_transformers import SentenceTransformer
from PIL import Image

# 1. 페이지 레이아웃 및 리소스 로드
st.set_page_config(layout="wide", page_title="Doosan Robotics Smart RAG")

@st.cache_resource
def load_resources():
    # 임베딩 모델 로드
    model = SentenceTransformer('BAAI/bge-m3')
    # Vector DB 연결
    client = chromadb.PersistentClient(path="./rag_db")
    collection = client.get_collection(name="doosan_manual_collection")
    return model, collection

model, collection = load_resources()

# --- Qwen 2.5 1.5B 답변 생성 함수 (Ollama API) ---
def generate_answer(question, context):
    url = "http://localhost:11434/api/generate"
    # 전문가 페르소나 부여 프롬프트
    prompt = f"""
    당신은 두산로보틱스의 협동로봇 기술지원 전문가입니다. 
    아래 [매뉴얼 내용]을 기반으로 사용자의 [질문]에 대해 신뢰감 있고 친절하게 한국어로 답변하세요.
    내용에 없는 사실을 지어내지 말고, 기술적인 수치나 안전 관련 정보는 매뉴얼 내용을 정확히 인용하세요.

    [매뉴얼 내용]:
    {context}

    [질문]:
    {question}
    
    답변:
    """
    
    data = {
        "model": "qwen2.5:1.5b", 
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=180)
        res_json = response.json()
        
        if 'response' in res_json:
            return res_json['response']
        else:
            return f"⚠️ Ollama 응답 형식 오류: {res_json}"
            
    except requests.exceptions.Timeout:
        return "⏳ Qwen 2.5:1.5b가 답변을 생성하는 데 시간이 너무 오래 걸립니다."
    except Exception as e:
        return f"❌ 연동 실패: {e}"

# 2. 사이드바
with st.sidebar:
    st.title("🤖 Intelligent Assistant")
    st.info("BGE-M3 + ChromaDB + Qwen 2.5 1.5B")
    st.write("✅ **LLM:** qwen2.5:1.5b")
    st.write("✅ **Embedder:** BGE-M3")
    st.write("✅ **Vector DB:** ChromaDB")
    st.markdown("---")
    st.write("※ 터미널에서 `ollama run qwen2.5:1.5b`가 실행 중이어야 합니다.")

# 3. 메인 인터페이스
st.header("🦾 두산로보틱스 지능형 Q&A 시스템")
st.caption("텍스트 매뉴얼 검색과 이미지 참조를 동시에 지원하는 멀티모달 RAG입니다.")

query = st.text_input("질문을 입력하세요", placeholder="예: 서보 온(Servo On) 절차를 알려줘")

if query:
    # [수정완료] n_results=5 로 Top-5 검색
    query_embedding = model.encode(query).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=5)

    if results['documents'] and len(results['documents'][0]) > 0:
        retrieved_docs = results['documents'][0]
        retrieved_metas = results['metadatas'][0]
        
        # [수정완료] Top-5 문서를 랭킹 순으로 하나의 종합 컨텍스트로 병합
        combined_context = ""
        for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas)):
            combined_context += f"[관련도 {i+1}순위 자료 | 출처: {meta['heading']} (페이지 {meta['pages']})]\n{doc}\n\n"

        # Top-5 문서를 순회하며 이미지를 수집 (중복 제거, 출처 기록)
        collected_images = []
        seen_paths = set()
        for rank, meta in enumerate(retrieved_metas):
            paths = json.loads(meta['linked_images'])
            for img_p in paths:
                if img_p not in seen_paths and os.path.exists(img_p):
                    seen_paths.add(img_p)
                    collected_images.append({
                        "path": img_p,
                        "rank": rank + 1,
                        "heading": meta['heading'],
                        "pages": meta['pages']
                    })

        with st.spinner('Qwen 2.5:1.5b가 Top-5 매뉴얼 문서를 종합 분석 중입니다...'):
            ai_answer = generate_answer(query, combined_context)

        # 결과 렌더링
        col1, col2 = st.columns([0.6, 0.4])

        with col1:
            st.markdown("### 🤖 로봇 메뉴얼 답변")
            st.write(ai_answer)

            with st.expander("📌 참조한 Top-5 매뉴얼 원문 (Ground Truth)"):
                for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metas)):
                    st.success(f"**[{i+1}순위] Section:** {meta['heading']} (Page {meta['pages']})")
                    st.write(doc)
                    st.divider()

        with col2:
            st.markdown("### 🖼️ 참조 가이드 (Vision)")
            if collected_images:
                for img_info in collected_images:
                    image = Image.open(img_info["path"])
                    caption = f"[{img_info['rank']}순위] {img_info['heading']} (Page {img_info['pages']})"
                    st.image(image, use_container_width=True, caption=caption)
            else:
                st.warning("Top-5 검색 결과에서 연관된 기술 도식을 찾을 수 없습니다.")
    else:
        st.error("매뉴얼에서 관련 정보를 찾지 못했습니다.")