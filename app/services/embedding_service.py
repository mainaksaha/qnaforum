from functools import cached_property
import numpy as np
from app.core.config import settings


class EmbeddingService:
    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.embedding_model)

    @property
    def model_name(self) -> str:
        return settings.embedding_model

    @property
    def dimension(self) -> int:
        return len(self.embed_query("dimension probe"))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return vec.tolist()

    @staticmethod
    def normalize(vec: list[float]) -> list[float]:
        arr = np.array(vec, dtype=np.float32)
        denom = np.linalg.norm(arr)
        if denom == 0:
            return arr.tolist()
        return (arr / denom).tolist()
