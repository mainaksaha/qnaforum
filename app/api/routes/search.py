from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.schemas.search import SearchRequest
from app.repositories.problems import ProblemRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.repositories.vector_documents import VectorDocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.faiss_index_service import FaissIndexService
from app.services.search_service import SearchService

router = APIRouter(tags=["search"])


@router.post("/search")
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    faiss_svc = FaissIndexService()
    try:
        dim = EmbeddingService().dimension
        faiss_svc.load_or_create_index(dim)
    except Exception:
        pass
    svc = SearchService(db, ProblemRepository(db), SearchDocumentRepository(db), VectorDocumentRepository(db), EmbeddingService(), faiss_svc)
    return {"query": payload.query, "mode": payload.mode, "results": svc.search(payload.query, payload.mode, payload.top_k)}
