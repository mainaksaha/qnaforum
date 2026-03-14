from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.audit_event import AuditEvent


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> AuditEvent:
        ev = AuditEvent(**kwargs)
        self.db.add(ev)
        self.db.flush()
        return ev

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        return list(self.db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)))
