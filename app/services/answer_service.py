from app.core.security import utcnow_iso
from app.models.answer import Answer
from app.models.problem import Problem
from app.repositories.answers import AnswerRepository
from app.repositories.problems import ProblemRepository


class AnswerService:
    def __init__(self, repo: AnswerRepository, problems: ProblemRepository):
        self.repo = repo
        self.problems = problems

    def create(self, user_id: int, problem: Problem, body_markdown: str, kind: str) -> Answer:
        now = utcnow_iso()
        ext = f"A-{(len(self.repo.list_for_problem(problem.id))+1):06d}"
        ans = self.repo.create(external_id=ext, problem_id=problem.id, body_markdown=body_markdown, author_user_id=user_id, kind=kind, version=1, created_at=now, updated_at=now)
        if problem.status == "open":
            problem.status = "answered"
        problem.last_activity_at = now
        return ans
