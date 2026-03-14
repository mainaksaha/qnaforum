from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.problem import Problem


class ProblemRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, limit: int = 20, offset: int = 0) -> list[Problem]:
        return list(self.db.scalars(select(Problem).order_by(Problem.last_activity_at.desc()).offset(offset).limit(limit)))

    def get_by_external_id(self, external_id: str) -> Problem | None:
        return self.db.scalar(select(Problem).where(Problem.external_id == external_id))

    def get(self, problem_id: int) -> Problem | None:
        return self.db.get(Problem, problem_id)

    def create(self, **kwargs) -> Problem:
        obj = Problem(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj
