from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = os.getenv("QNA_APP_NAME", "QnA Forum")
    database_url: str = os.getenv("QNA_DATABASE_URL", "sqlite:///./data/qna.db")
    data_dir: str = os.getenv("QNA_DATA_DIR", "data")
    faiss_index_path: str = os.getenv("QNA_FAISS_INDEX_PATH", "data/faiss/qna.index")
    embedding_model: str = os.getenv("QNA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    api_base_path: str = "/api/v1"


settings = Settings()
