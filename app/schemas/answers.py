from pydantic import BaseModel
from typing import Literal


class CreateAnswerRequest(BaseModel):
    body_markdown: str
    kind: Literal["reply", "solution", "update"] = "reply"


class UpdateAnswerRequest(BaseModel):
    body_markdown: str
