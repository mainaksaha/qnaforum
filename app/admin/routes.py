from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.repositories.users import UserRepository
from app.repositories.api_keys import ApiKeyRepository
from app.repositories.audit import AuditRepository
from app.repositories.problems import ProblemRepository
from app.repositories.answers import AnswerRepository
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    users = UserRepository(db).list_users()
    keys = sum(len(ApiKeyRepository(db).list_for_user(u.id)) for u in users)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "users": len(users), "keys": keys, "problems": len(ProblemRepository(db).list(10000,0)), "answers": len(db.query(__import__('app.models.answer', fromlist=['Answer']).Answer).all())})


@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": UserRepository(db).list_users()})


@router.post("/users")
def create_user(username: str = Form(...), display_name: str = Form(...), email: str = Form(default=""), role: str = Form(default="user"), db: Session = Depends(get_db)):
    AdminService(UserRepository(db), ApiKeyRepository(db)).create_user(username, display_name, email or None, role)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/users/{user_id}")
def user_detail(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = UserRepository(db).get(user_id)
    keys = ApiKeyRepository(db).list_for_user(user_id)
    return templates.TemplateResponse("admin/user_detail.html", {"request": request, "user": user, "keys": keys})


@router.post("/users/{user_id}/issue-key")
def issue_key(user_id: int, db: Session = Depends(get_db)):
    raw = AdminService(UserRepository(db), ApiKeyRepository(db)).issue_api_key(user_id, "issued via admin")
    db.commit()
    return {"api_key": raw}


@router.get("/audit")
def audit_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/audit.html", {"request": request, "events": AuditRepository(db).list_recent(100)})
