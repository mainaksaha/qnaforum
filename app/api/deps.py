from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.repositories.users import UserRepository
from app.repositories.api_keys import ApiKeyRepository
from app.services.auth_service import AuthService


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.replace("Bearer ", "", 1)
    auth = AuthService(UserRepository(db), ApiKeyRepository(db))
    user = auth.authenticate_key(token)
    if not user:
        raise HTTPException(401, "Invalid API key")
    db.commit()
    return user
