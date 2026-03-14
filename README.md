# QnA Forum MVP

Lightweight FastAPI + SQLite + FTS5 + FAISS Q&A forum for API/CLI-first usage.

## Quickstart

```bash
python -m app.scripts.init_db
python -m app.scripts.seed_demo_data
uvicorn main:app --reload
```

## Rebuild vectors

```bash
python -m app.scripts.rebuild_faiss
```
