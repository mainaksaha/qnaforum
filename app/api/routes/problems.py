from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.db import get_db
from app.repositories.problems import ProblemRepository
from app.repositories.answers import AnswerRepository
from app.repositories.tags import TagRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.schemas.problems import CreateProblemRequest, UpdateProblemRequest
from app.services.problem_service import ProblemService
from app.services.search_document_service import SearchDocumentService

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("")
def list_problems(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    repo = ProblemRepository(db)
    return [{"external_id": p.external_id, "title": p.title, "status": p.status} for p in repo.list(limit, offset)]


@router.get("/{problem_id}")
def get_problem(problem_id: str, db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    answers = AnswerRepository(db)
    tags = TagRepository(db)
    p = probs.get_by_external_id(problem_id)
    if not p:
        raise HTTPException(404, "Problem not found")
    return {
        "external_id": p.external_id,
        "title": p.title,
        "body_markdown": p.body_markdown,
        "status": p.status,
        "tags": tags.get_problem_tags(p.id),
        "answers": [{"external_id": a.external_id, "body_markdown": a.body_markdown, "kind": a.kind} for a in answers.list_for_problem(p.id)],
    }


@router.post("")
def create_problem(payload: CreateProblemRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    tags = TagRepository(db)
    service = ProblemService(probs, tags)
    p = service.create(user.id, payload.title, payload.body_markdown, payload.tags)
    SearchDocumentService(SearchDocumentRepository(db), AnswerRepository(db), tags).sync_problem_documents(p)
    db.commit()
    return {"external_id": p.external_id}


@router.patch("/{problem_id}")
def update_problem(problem_id: str, payload: UpdateProblemRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    tags = TagRepository(db)
    p = probs.get_by_external_id(problem_id)
    if not p:
        raise HTTPException(404, "Problem not found")
    if p.author_user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Only the author or admin may update")
    if payload.title is not None:
        p.title = payload.title
    if payload.body_markdown is not None:
        p.body_markdown = payload.body_markdown
    if payload.tags is not None:
        tags.set_problem_tags(p.id, payload.tags)
    SearchDocumentService(SearchDocumentRepository(db), AnswerRepository(db), tags).sync_problem_documents(p)
    db.commit()
    return {"ok": True}
