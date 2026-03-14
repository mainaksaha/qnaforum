from pydantic import BaseModel


class CreateProblemRequest(BaseModel):
    title: str
    body_markdown: str
    tags: list[str] = []


class UpdateProblemRequest(BaseModel):
    title: str | None = None
    body_markdown: str | None = None
    tags: list[str] | None = None
