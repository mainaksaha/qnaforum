from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_hash(self, key_hash: str) -> ApiKey | None:
        return self.db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.status == "active"))

    def list_for_user(self, user_id: int) -> list[ApiKey]:
        return list(self.db.scalars(select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.id.desc())))

    def create(self, **kwargs) -> ApiKey:
        obj = ApiKey(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj
