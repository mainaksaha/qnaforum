from pydantic import BaseModel
from typing import Literal


class SearchRequest(BaseModel):
    query: str
    mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    top_k: int = 10
    filters: dict | None = None
    include_answers: bool = True
