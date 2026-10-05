import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from app.rag.sop import BASE_DIR, KNOWLEDGE_BASE_PATH, load_sops


CHROMA_PATH = Path(os.getenv("CHROMA_PATH", BASE_DIR / "chroma_db"))

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "langchain"


def load_documents(knowledge_base_path: Path = KNOWLEDGE_BASE_PATH):
    return [
        Document(
            page_content=sop["content"],
            # What the SOP applies to is stored with every chunk, so
            # retrieval can be limited to the incident's application.
            metadata={
                "source": sop["source"],
                "application": sop["application"],
                "priority": sop["priority"]
            }
        )
        for sop in load_sops(knowledge_base_path)
    ]


def ingest(
    knowledge_base_path: Path = KNOWLEDGE_BASE_PATH,
    chroma_path: Path = CHROMA_PATH
) -> int:
    """
    Build the SOP vector index and return the number of chunks stored.

    Existing chunks are replaced each time, so running the ingest again
    never leaves duplicate chunks behind.
    """

    print("Loading knowledge base...")

    documents = load_documents(knowledge_base_path)

    print(f"Loaded {len(documents)} documents")

    if not documents:
        raise RuntimeError(
            f"No .md files found in {knowledge_base_path}"
        )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = text_splitter.split_documents(documents)

    print(f"Created {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    print("Creating Chroma vector database...")

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(chroma_path),
        embedding_function=embeddings
    )

    # Clear the old chunks in place. The collection itself is kept so a
    # running API, which already has it open, keeps working.
    existing_ids = vectorstore.get()["ids"]

    if existing_ids:
        vectorstore.delete(ids=existing_ids)

    # Stable IDs keep each chunk unique within the index.
    ids = [
        f"{chunk.metadata['source']}-{index}"
        for index, chunk in enumerate(chunks)
    ]

    vectorstore.add_documents(
        documents=chunks,
        ids=ids
    )

    print("Knowledge base successfully ingested.")

    return len(chunks)


if __name__ == "__main__":
    ingest()
