from app.core.security import hash_api_key, utcnow_iso
from app.repositories.api_keys import ApiKeyRepository
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, key_repo: ApiKeyRepository):
        self.user_repo = user_repo
        self.key_repo = key_repo

    def authenticate_key(self, raw_key: str):
        key_hash = hash_api_key(raw_key)
        api_key = self.key_repo.get_active_by_hash(key_hash)
        if not api_key:
            return None
        user = self.user_repo.get(api_key.user_id)
        if not user or user.status != "active":
            return None
        api_key.last_used_at = utcnow_iso()
        return user
