from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.answer import Answer


class AnswerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_problem(self, problem_id: int) -> list[Answer]:
        return list(self.db.scalars(select(Answer).where(Answer.problem_id == problem_id).order_by(Answer.created_at.asc())))

    def get_by_external_id(self, external_id: str) -> Answer | None:
        return self.db.scalar(select(Answer).where(Answer.external_id == external_id))

    def get(self, answer_id: int) -> Answer | None:
        return self.db.get(Answer, answer_id)

    def create(self, **kwargs) -> Answer:
        obj = Answer(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj
