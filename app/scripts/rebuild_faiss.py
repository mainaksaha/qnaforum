from app.core.db import SessionLocal
from app.repositories.search_documents import SearchDocumentRepository
from app.repositories.vector_documents import VectorDocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.faiss_index_service import FaissIndexService
from app.core.security import utcnow_iso


def main():
    db = SessionLocal()
    try:
        docs_repo = SearchDocumentRepository(db)
        vec_repo = VectorDocumentRepository(db)
        emb = EmbeddingService()
        faiss = FaissIndexService()
        faiss.load_or_create_index(emb.dimension)
        for doc in docs_repo.list_active():
            vec = emb.embed_query(doc.search_text)
            vector_id = vec_repo.next_vector_id()
            faiss.add_or_replace(vector_id, vec)
            vec_repo.upsert(search_document_id=doc.id, faiss_vector_id=vector_id, embedding_model=emb.model_name, embedding_dim=len(vec), is_active=1, updated_at=utcnow_iso())
        faiss.save()
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
