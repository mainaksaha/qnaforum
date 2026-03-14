from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.search_document import SearchDocument


class SearchDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_problem_and_type(self, problem_id: int, doc_type: str) -> SearchDocument | None:
        return self.db.scalar(select(SearchDocument).where(SearchDocument.problem_id == problem_id, SearchDocument.doc_type == doc_type))

    def upsert(self, problem_id: int, doc_type: str, source_checksum: str, search_text: str, fts_title: str, fts_body: str, updated_at: str) -> SearchDocument:
        doc = self.get_by_problem_and_type(problem_id, doc_type)
        if not doc:
            doc = SearchDocument(problem_id=problem_id, doc_type=doc_type, source_checksum=source_checksum, search_text=search_text, fts_title=fts_title, fts_body=fts_body, status="active", updated_at=updated_at)
            self.db.add(doc)
        else:
            doc.source_checksum = source_checksum
            doc.search_text = search_text
            doc.fts_title = fts_title
            doc.fts_body = fts_body
            doc.updated_at = updated_at
        self.db.flush()
        return doc

    def list_active(self) -> list[SearchDocument]:
        return list(self.db.scalars(select(SearchDocument).where(SearchDocument.status == "active")))
