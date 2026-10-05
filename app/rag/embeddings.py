"""
Embeddings for the SOP index.

Uses Chroma's built-in ONNX build of all-MiniLM-L6-v2. It is the same model
as the sentence-transformers one, but runs on onnxruntime, so the app does
not need torch (about 100 MB of memory instead of over 1 GB).
"""

from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from langchain_core.embeddings import Embeddings


class OnnxMiniLMEmbeddings(Embeddings):
    def __init__(self) -> None:
        self._model = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vector] for vector in self._model(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
