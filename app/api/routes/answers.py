from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.db import get_db
from app.repositories.answers import AnswerRepository
from app.repositories.problems import ProblemRepository
from app.repositories.tags import TagRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.schemas.answers import CreateAnswerRequest, UpdateAnswerRequest
from app.services.answer_service import AnswerService
from app.services.search_document_service import SearchDocumentService

router = APIRouter(tags=["answers"])


@router.post("/problems/{problem_id}/answers")
def create_answer(problem_id: str, payload: CreateAnswerRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    p = probs.get_by_external_id(problem_id)
    if not p:
        raise HTTPException(404, "Problem not found")
    ans = AnswerService(AnswerRepository(db), probs).create(user.id, p, payload.body_markdown, payload.kind)
    SearchDocumentService(SearchDocumentRepository(db), AnswerRepository(db), TagRepository(db)).sync_problem_documents(p)
    db.commit()
    return {"external_id": ans.external_id}


@router.patch("/answers/{answer_id}")
def update_answer(answer_id: str, payload: UpdateAnswerRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    answers = AnswerRepository(db)
    probs = ProblemRepository(db)
    a = answers.get_by_external_id(answer_id)
    if not a:
        raise HTTPException(404, "Answer not found")
    if a.author_user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Only the author or admin may update this answer")
    a.body_markdown = payload.body_markdown
    a.version += 1
    p = probs.get(a.problem_id)
    SearchDocumentService(SearchDocumentRepository(db), answers, TagRepository(db)).sync_problem_documents(p)
    db.commit()
    return {"ok": True}


@router.post("/problems/{problem_id}/accept-answer")
def accept_answer(problem_id: str, answer_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    answers = AnswerRepository(db)
    p = probs.get_by_external_id(problem_id)
    if not p:
        raise HTTPException(404, "Problem not found")
    if p.author_user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Only problem owner or admin")
    a = answers.get_by_external_id(answer_id)
    if not a or a.problem_id != p.id:
        raise HTTPException(400, "Invalid answer for this problem")
    p.accepted_answer_id = a.id
    p.status = "resolved"
    SearchDocumentService(SearchDocumentRepository(db), answers, TagRepository(db)).sync_problem_documents(p)
    db.commit()
    return {"ok": True}


@router.post("/problems/{problem_id}/set-canonical-solution")
def set_canonical(problem_id: str, answer_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    probs = ProblemRepository(db)
    answers = AnswerRepository(db)
    p = probs.get_by_external_id(problem_id)
    if not p:
        raise HTTPException(404, "Problem not found")
    if p.author_user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Only problem owner or admin")
    a = answers.get_by_external_id(answer_id)
    if not a or a.problem_id != p.id:
        raise HTTPException(400, "Invalid answer for this problem")
    p.canonical_solution_answer_id = a.id
    p.status = "resolved"
    SearchDocumentService(SearchDocumentRepository(db), answers, TagRepository(db)).sync_problem_documents(p)
    db.commit()
    return {"ok": True}
