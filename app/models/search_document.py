from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class SearchDocument(Base):
    __tablename__ = "search_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String, nullable=False)
    search_text: Mapped[str] = mapped_column(String, nullable=False)
    fts_title: Mapped[str] = mapped_column(String, nullable=False)
    fts_body: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
