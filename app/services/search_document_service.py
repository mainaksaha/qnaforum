import hashlib
from app.core.security import utcnow_iso
from app.models.problem import Problem
from app.repositories.answers import AnswerRepository
from app.repositories.search_documents import SearchDocumentRepository
from app.repositories.tags import TagRepository


class SearchDocumentService:
    def __init__(self, docs: SearchDocumentRepository, answers: AnswerRepository, tags: TagRepository):
        self.docs = docs
        self.answers = answers
        self.tags = tags

    def _checksum(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def sync_problem_documents(self, problem: Problem):
        tags = self.tags.get_problem_tags(problem.id)
        answers = self.answers.list_for_problem(problem.id)
        accepted = next((a for a in answers if a.id == problem.accepted_answer_id), None)
        canonical = next((a for a in answers if a.id == problem.canonical_solution_answer_id), None)
        problem_doc_text = f"{problem.title}\n{problem.body_markdown}\n{' '.join(tags)}"
        bundle_doc_text = "\n".join(
            [problem.title, problem.body_markdown, " ".join(tags), accepted.body_markdown if accepted else "", canonical.body_markdown if canonical else ""]
        )
        now = utcnow_iso()
        self.docs.upsert(problem.id, "problem_doc", self._checksum(problem_doc_text), problem_doc_text, problem.title, problem.body_markdown, now)
        self.docs.upsert(problem.id, "problem_bundle_doc", self._checksum(bundle_doc_text), bundle_doc_text, problem.title, bundle_doc_text, now)
