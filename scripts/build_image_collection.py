import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from image_index import IMAGE_COLLECTION_NAME, build_image_search_collection  # noqa: E402
from paths import (  # noqa: E402
    FINAL_PROCESSING_REPORT_PATH,
    TEXT_CHUNKS_PATH,
    VECTOR_DB_DIR,
    configure_model_cache,
)


def main():
    configure_model_cache()
    text_chunks = json.loads(TEXT_CHUNKS_PATH.read_text(encoding="utf-8"))
    image_metadata = json.loads(FINAL_PROCESSING_REPORT_PATH.read_text(encoding="utf-8"))

    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    embedding_model = SentenceTransformer("BAAI/bge-m3")
    collection = build_image_search_collection(
        text_chunks=text_chunks,
        image_metadata=image_metadata,
        embedding_model=embedding_model,
        client=client,
        reset=True,
    )
    print(f"{IMAGE_COLLECTION_NAME} built: {collection.count()} images")


if __name__ == "__main__":
    main()
