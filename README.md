# Multimodal Offline RAG System

Doosan Robotics collaborative robot manual PDFs are used to build an offline multimodal RAG system that retrieves text chunks and related technical images, then generates answers with a local LLM.

## System Overview

```text
PDF manuals
-> text and image extraction
-> text chunking
-> SigLIP-based technical image filtering
-> bbox-based text-image mapping
-> BGE-M3 text embedding
-> ChromaDB vector storage
-> Streamlit question answering UI
-> Ollama local LLM answer generation
```

## Folder Structure

```text
src/                  Python pipeline and app code
scripts/              Setup and utility scripts
data/raw/             Original PDF manuals
data/processed/       Text chunks, image metadata, extracted images
data/evaluation/      Evaluation CSV/XLSX files
data/vector_db/       ChromaDB vector database
docs/                 Research notes and project documents
models/               Local model files, ignored by Git
runtime/              Local Ollama runtime files, ignored by Git
```

## GitHub Repository Notes

The repository includes source code, manual PDFs, processed data, evaluation files, and the current ChromaDB database.

The following local runtime files are intentionally excluded because they are large or machine-specific:

```text
.venv/
.python/
models/siglip_local/
models/hf_cache/
runtime/ollama/
runtime/ollama_home/
runtime/ollama_models/
runtime/downloads/
```

To run the project on another machine, Python dependencies, SigLIP/BGE-M3 model cache, Ollama, and local LLM models must be installed or downloaded again.

## Preprocessing

Run the preprocessing pipeline in this order:

```powershell
.\.venv\Scripts\python.exe src\unified_extractor.py
.\.venv\Scripts\python.exe src\text_filter.py
.\.venv\Scripts\python.exe src\embedding_text_image.py
```

If SigLIP is not available locally, download it first:

```powershell
.\.venv\Scripts\python.exe scripts\download_siglip.py
```

## Run App

Start Ollama:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_ollama.ps1
```

Run the Streamlit app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app.py
```

Gemma version:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\app_gemma.py
```

## Current Models

```text
Embedding model: BAAI/bge-m3
Image filtering model: google/siglip-base-patch16-224
Local LLM: qwen2.5:1.5b / gemma2:2b through Ollama
```

## Planned Improvements

```text
1. Add preprocessing-time SigLIP image-text similarity for better text-image mapping.
2. Compare small local LLMs with 4-bit quantized 7B-8B class local LLMs.
3. Evaluate text-image mapping accuracy, Top-k retrieval, and LLM answer quality.
```
