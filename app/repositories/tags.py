from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.tag import Tag, ProblemTag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> Tag:
        found = self.db.scalar(select(Tag).where(Tag.name == name))
        if found:
            return found
        tag = Tag(name=name)
        self.db.add(tag)
        self.db.flush()
        return tag

    def set_problem_tags(self, problem_id: int, tags: list[str]) -> None:
        self.db.query(ProblemTag).filter(ProblemTag.problem_id == problem_id).delete()
        for tag_name in tags:
            tag = self.get_or_create(tag_name.strip())
            self.db.add(ProblemTag(problem_id=problem_id, tag_id=tag.id))

    def get_problem_tags(self, problem_id: int) -> list[str]:
        rows = self.db.query(Tag.name).join(ProblemTag, ProblemTag.tag_id == Tag.id).filter(ProblemTag.problem_id == problem_id).all()
        return [r[0] for r in rows]
