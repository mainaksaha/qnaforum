from sqlalchemy import text
from app.repositories.problems import ProblemRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.repositories.vector_documents import VectorDocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.faiss_index_service import FaissIndexService


class SearchService:
    def __init__(self, db, probs: ProblemRepository, docs: SearchDocumentRepository, vectors: VectorDocumentRepository, embed: EmbeddingService, faiss_svc: FaissIndexService):
        self.db = db
        self.probs = probs
        self.docs = docs
        self.vectors = vectors
        self.embed = embed
        self.faiss = faiss_svc

    def keyword_search(self, query: str, top_k: int):
        sql = text("""
            SELECT sd.problem_id, bm25(search_documents_fts) AS score
            FROM search_documents_fts
            JOIN search_documents sd ON sd.id = search_documents_fts.rowid
            WHERE search_documents_fts MATCH :q
            ORDER BY score
            LIMIT :k
        """)
        return [{"problem_id": r.problem_id, "score": float(-r.score)} for r in self.db.execute(sql, {"q": query, "k": top_k})]

    def semantic_search(self, query: str, top_k: int):
        qv = self.embed.embed_query(query)
        hits = self.faiss.search(qv, top_k)
        active = {v.faiss_vector_id: v.search_document_id for v in self.vectors.list_active()}
        out = []
        for vid, score in hits:
            doc_id = active.get(vid)
            if not doc_id:
                continue
            doc = self.db.get(__import__('app.models.search_document', fromlist=['SearchDocument']).SearchDocument, doc_id)
            if doc:
                out.append({"problem_id": doc.problem_id, "score": score})
        return out

    def search(self, query: str, mode: str, top_k: int = 10):
        bucket = {}
        if mode in ("keyword", "hybrid"):
            for hit in self.keyword_search(query, top_k):
                bucket.setdefault(hit["problem_id"], {"keyword": 0.0, "semantic": 0.0})["keyword"] = max(bucket[hit["problem_id"]]["keyword"], hit["score"])
        if mode in ("semantic", "hybrid"):
            for hit in self.semantic_search(query, top_k):
                bucket.setdefault(hit["problem_id"], {"keyword": 0.0, "semantic": 0.0})["semantic"] = max(bucket[hit["problem_id"]]["semantic"], hit["score"])
        results = []
        for pid, scores in bucket.items():
            p = self.probs.get(pid)
            if not p:
                continue
            final_score = 0.7 * scores["semantic"] + 0.2 * scores["keyword"] + (0.1 if p.status == "resolved" else 0.0)
            results.append({"problem_id": p.external_id, "title": p.title, "score": final_score, "status": p.status})
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
