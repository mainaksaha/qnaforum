from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.routes.health import router as health_router
from app.api.routes.problems import router as problems_router
from app.api.routes.answers import router as answers_router
from app.api.routes.search import router as search_router
from app.admin.routes import router as admin_router
from app.core.config import settings
from app.core.db import get_db
from app.repositories.problems import ProblemRepository
from app.repositories.answers import AnswerRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.repositories.vector_documents import VectorDocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.faiss_index_service import FaissIndexService
from app.services.search_service import SearchService

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(health_router, prefix=settings.api_base_path)
app.include_router(problems_router, prefix=settings.api_base_path)
app.include_router(answers_router, prefix=settings.api_base_path)
app.include_router(search_router, prefix=settings.api_base_path)
app.include_router(admin_router)


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    problems = ProblemRepository(db).list(limit=30, offset=0)
    return templates.TemplateResponse("index.html", {"request": request, "problems": problems})


@app.get("/search")
def web_search(request: Request, q: str = "", db: Session = Depends(get_db)):
    results = []
    if q:
        faiss_svc = FaissIndexService()
        try:
            faiss_svc.load_or_create_index(EmbeddingService().dimension)
            results = SearchService(db, ProblemRepository(db), SearchDocumentRepository(db), VectorDocumentRepository(db), EmbeddingService(), faiss_svc).search(q, "hybrid", 20)
        except Exception:
            results = SearchService(db, ProblemRepository(db), SearchDocumentRepository(db), VectorDocumentRepository(db), EmbeddingService(), FaissIndexService()).search(q, "keyword", 20)
    return templates.TemplateResponse("search.html", {"request": request, "q": q, "results": results})


@app.get("/problems/{external_id}")
def problem_detail(external_id: str, request: Request, db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    p = probs.get_by_external_id(external_id)
    answers = []
    if p:
        answers = AnswerRepository(db).list_for_problem(p.id)
    return templates.TemplateResponse("problem_detail.html", {"request": request, "problem": p, "answers": answers})
