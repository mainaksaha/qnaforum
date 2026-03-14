from sqlalchemy import text
from fastapi.testclient import TestClient

from main import app
from app.core.db import Base, SessionLocal, engine
from app.repositories.api_keys import ApiKeyRepository
from app.repositories.users import UserRepository
from app.services.admin_service import AdminService


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS search_documents_fts USING fts5(
                  fts_title,
                  fts_body,
                  content='search_documents',
                  content_rowid='id'
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS search_documents_ai AFTER INSERT ON search_documents BEGIN
                  INSERT INTO search_documents_fts(rowid, fts_title, fts_body)
                  VALUES (new.id, new.fts_title, new.fts_body);
                END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS search_documents_ad AFTER DELETE ON search_documents BEGIN
                  INSERT INTO search_documents_fts(search_documents_fts, rowid, fts_title, fts_body)
                  VALUES ('delete', old.id, old.fts_title, old.fts_body);
                END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS search_documents_au AFTER UPDATE ON search_documents BEGIN
                  INSERT INTO search_documents_fts(search_documents_fts, rowid, fts_title, fts_body)
                  VALUES ('delete', old.id, old.fts_title, old.fts_body);
                  INSERT INTO search_documents_fts(rowid, fts_title, fts_body)
                  VALUES (new.id, new.fts_title, new.fts_body);
                END;
                """
            )
        )


def seed_users_and_keys() -> dict[str, str]:
    db = SessionLocal()
    try:
        admin_svc = AdminService(UserRepository(db), ApiKeyRepository(db))
        owner = admin_svc.create_user("owner", "Owner", "owner@example.com", "user")
        helper = admin_svc.create_user("helper", "Helper", "helper@example.com", "user")
        admin = admin_svc.create_user("admin", "Admin", "admin@example.com", "admin")
        owner_key = admin_svc.issue_api_key(owner.id, "owner key")
        helper_key = admin_svc.issue_api_key(helper.id, "helper key")
        admin_key = admin_svc.issue_api_key(admin.id, "admin key")
        db.commit()
        return {"owner": owner_key, "helper": helper_key, "admin": admin_key}
    finally:
        db.close()


def auth_header(raw_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_key}"}


def test_problem_answer_accept_and_canonical_flow():
    reset_db()
    keys = seed_users_and_keys()
    client = TestClient(app)

    create_problem = client.post(
        "/api/v1/problems",
        headers=auth_header(keys["owner"]),
        json={
            "title": "How do I rotate API keys safely?",
            "body_markdown": "I need zero downtime rotation for service-to-service auth.",
            "tags": ["auth", "api"],
        },
    )
    assert create_problem.status_code == 200
    problem_id = create_problem.json()["external_id"]

    helper_answer = client.post(
        f"/api/v1/problems/{problem_id}/answers",
        headers=auth_header(keys["helper"]),
        json={"body_markdown": "Use overlapping validity windows.", "kind": "solution"},
    )
    assert helper_answer.status_code == 200
    answer_id = helper_answer.json()["external_id"]

    accept = client.post(
        f"/api/v1/problems/{problem_id}/accept-answer",
        headers=auth_header(keys["owner"]),
        params={"answer_id": answer_id},
    )
    assert accept.status_code == 200

    canonical = client.post(
        f"/api/v1/problems/{problem_id}/set-canonical-solution",
        headers=auth_header(keys["owner"]),
        params={"answer_id": answer_id},
    )
    assert canonical.status_code == 200

    detail = client.get(f"/api/v1/problems/{problem_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "resolved"
    assert payload["answers"][0]["external_id"] == answer_id


def test_keyword_search_returns_indexed_problem():
    reset_db()
    keys = seed_users_and_keys()
    client = TestClient(app)

    create_problem = client.post(
        "/api/v1/problems",
        headers=auth_header(keys["owner"]),
        json={
            "title": "Unhandled E_CONNRESET in job runner",
            "body_markdown": "Workers fail with E_CONNRESET when upstream closes sockets.",
            "tags": ["network", "errors"],
        },
    )
    assert create_problem.status_code == 200

    search = client.post(
        "/api/v1/search",
        json={"query": "E_CONNRESET", "mode": "keyword", "top_k": 5},
    )
    assert search.status_code == 200
    results = search.json()["results"]
    assert any("E_CONNRESET" in r["title"] for r in results)


def test_revoked_key_is_blocked():
    reset_db()
    keys = seed_users_and_keys()
    client = TestClient(app)

    db = SessionLocal()
    try:
        api_keys = ApiKeyRepository(db).list_for_user(UserRepository(db).get_by_username("owner").id)
        api_keys[0].status = "revoked"
        db.commit()
    finally:
        db.close()

    denied = client.post(
        "/api/v1/problems",
        headers=auth_header(keys["owner"]),
        json={"title": "x", "body_markdown": "y", "tags": []},
    )
    assert denied.status_code == 401


def test_admin_ui_user_create_and_issue_key():
    reset_db()
    seed_users_and_keys()
    client = TestClient(app)

    create = client.post(
        "/admin/users",
        data={"username": "newuser", "display_name": "New User", "email": "n@example.com", "role": "user"},
        follow_redirects=False,
    )
    assert create.status_code == 303

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_username("newuser")
        assert user is not None
        issue = client.post(f"/admin/users/{user.id}/issue-key")
        assert issue.status_code == 200
        assert issue.json()["api_key"].startswith("qna_")
    finally:
        db.close()


def test_no_admin_api_exists_under_api_prefix():
    reset_db()
    client = TestClient(app)
    resp = client.get("/api/v1/admin")
    assert resp.status_code == 404
