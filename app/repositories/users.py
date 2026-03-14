from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.id.desc())))

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.flush()
        return user
