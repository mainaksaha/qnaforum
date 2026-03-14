from sqlalchemy import text
from app.core.db import engine
from app.models import *  # noqa
from app.core.db import Base


def main():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS search_documents_fts USING fts5(
          fts_title,
          fts_body,
          content='search_documents',
          content_rowid='id'
        );
        """))
        conn.execute(text("""
        CREATE TRIGGER IF NOT EXISTS search_documents_ai AFTER INSERT ON search_documents BEGIN
          INSERT INTO search_documents_fts(rowid, fts_title, fts_body)
          VALUES (new.id, new.fts_title, new.fts_body);
        END;"""))
        conn.execute(text("""
        CREATE TRIGGER IF NOT EXISTS search_documents_ad AFTER DELETE ON search_documents BEGIN
          INSERT INTO search_documents_fts(search_documents_fts, rowid, fts_title, fts_body)
          VALUES ('delete', old.id, old.fts_title, old.fts_body);
        END;"""))
        conn.execute(text("""
        CREATE TRIGGER IF NOT EXISTS search_documents_au AFTER UPDATE ON search_documents BEGIN
          INSERT INTO search_documents_fts(search_documents_fts, rowid, fts_title, fts_body)
          VALUES ('delete', old.id, old.fts_title, old.fts_body);
          INSERT INTO search_documents_fts(rowid, fts_title, fts_body)
          VALUES (new.id, new.fts_title, new.fts_body);
        END;"""))


if __name__ == "__main__":
    main()
