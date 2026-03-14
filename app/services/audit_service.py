import json
from app.core.security import utcnow_iso
from app.repositories.audit import AuditRepository


class AuditService:
    def __init__(self, repo: AuditRepository):
        self.repo = repo

    def log(self, actor_user_id: int | None, event_type: str, entity_type: str, entity_id: str, payload: dict) -> None:
        self.repo.create(
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=json.dumps(payload),
            created_at=utcnow_iso(),
        )
