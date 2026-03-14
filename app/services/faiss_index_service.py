from pathlib import Path
import numpy as np
from app.core.config import settings


class FaissIndexService:
    def __init__(self):
        self.index = None
        self.dim = None

    def load_or_create_index(self, dim: int):
        import faiss

        self.dim = dim
        path = Path(settings.faiss_index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self.index = faiss.read_index(str(path))
        else:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        return self.index

    def add_or_replace(self, vector_id: int, embedding: list[float]):
        import faiss

        if self.index is None:
            raise RuntimeError("index not loaded")
        vec = np.array([embedding], dtype=np.float32)
        ids = np.array([vector_id], dtype=np.int64)
        self.index.add_with_ids(vec, ids)

    def search(self, query_embedding: list[float], top_k: int = 10) -> list[tuple[int, float]]:
        if self.index is None:
            return []
        vec = np.array([query_embedding], dtype=np.float32)
        scores, ids = self.index.search(vec, top_k)
        return [(int(i), float(s)) for s, i in zip(scores[0], ids[0]) if i != -1]

    def save(self):
        import faiss

        if self.index is None:
            return
        faiss.write_index(self.index, settings.faiss_index_path)
