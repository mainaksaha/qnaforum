from app.core.db import SessionLocal
from app.repositories.users import UserRepository
from app.repositories.api_keys import ApiKeyRepository
from app.services.admin_service import AdminService


def main():
    db = SessionLocal()
    try:
        svc = AdminService(UserRepository(db), ApiKeyRepository(db))
        if not UserRepository(db).get_by_username("admin"):
            admin = svc.create_user("admin", "Administrator", None, "admin")
            key = svc.issue_api_key(admin.id, "seed admin key")
            print("Admin API key:", key)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
