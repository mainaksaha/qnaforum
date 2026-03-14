from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.vector_document import VectorDocument


class VectorDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_vector_id(self) -> int:
        max_id = self.db.scalar(select(func.max(VectorDocument.faiss_vector_id)))
        return 0 if max_id is None else max_id + 1

    def upsert(self, **kwargs) -> VectorDocument:
        found = self.db.scalar(select(VectorDocument).where(VectorDocument.search_document_id == kwargs["search_document_id"], VectorDocument.is_active == 1))
        if found:
            found.is_active = 0
        obj = VectorDocument(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_active(self) -> list[VectorDocument]:
        return list(self.db.scalars(select(VectorDocument).where(VectorDocument.is_active == 1)))
