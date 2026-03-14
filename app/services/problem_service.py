from app.core.security import utcnow_iso
from app.models.problem import Problem
from app.repositories.problems import ProblemRepository
from app.repositories.tags import TagRepository


class ProblemService:
    def __init__(self, repo: ProblemRepository, tags: TagRepository):
        self.repo = repo
        self.tags = tags

    def create(self, user_id: int, title: str, body_markdown: str, tags: list[str]) -> Problem:
        now = utcnow_iso()
        ext = f"Q-{(len(self.repo.list(10000))+1):06d}"
        problem = self.repo.create(
            external_id=ext,
            title=title,
            body_markdown=body_markdown,
            author_user_id=user_id,
            status="open",
            created_at=now,
            updated_at=now,
            last_activity_at=now,
        )
        self.tags.set_problem_tags(problem.id, tags)
        return problem
