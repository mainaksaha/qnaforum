from fastapi import APIRouter
from app.core.db import engine

router = APIRouter()


@router.get("/health")
def health():
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return {"status": "ok"}
