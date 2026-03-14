from app.core.security import generate_api_key, hash_api_key, utcnow_iso
from app.repositories.users import UserRepository
from app.repositories.api_keys import ApiKeyRepository


class AdminService:
    def __init__(self, users: UserRepository, keys: ApiKeyRepository):
        self.users = users
        self.keys = keys

    def create_user(self, username: str, display_name: str, email: str | None, role: str = "user"):
        now = utcnow_iso()
        return self.users.create(username=username, display_name=display_name, email=email, role=role, status="active", created_at=now, updated_at=now)

    def issue_api_key(self, user_id: int, description: str | None = None):
        prefix, raw = generate_api_key()
        self.keys.create(user_id=user_id, key_prefix=prefix, key_hash=hash_api_key(raw), description=description, status="active", created_at=utcnow_iso())
        return raw
