# QnA Forum MVP

Lightweight, self-hostable Q&A forum designed for API-first and CLI-first usage, with a read-only public UI and an admin UI for user/API-key management.

## Features

- FastAPI backend (`/api/v1`)
- SQLite as source of truth
- SQLite FTS5 keyword search
- FAISS semantic search (derived index)
- Read-only public web UI
- Admin UI for users + API keys (no admin API)
- Typer-based CLI (`qna`)

## Requirements

- Python 3.11+
- SQLite with FTS5 support (typically available in standard Python SQLite builds)

## Project Layout

```text
app/
  api/              # API routes + auth dependency
  admin/            # Admin UI routes
  cli/              # Typer CLI entrypoint
  core/             # config/db/security helpers
  models/           # SQLAlchemy models
  repositories/     # DB access layer
  services/         # Business logic
  scripts/          # init/seed/rebuild scripts
  templates/        # Jinja templates for public/admin UI
  static/           # CSS assets
main.py             # FastAPI app
```

## Installation

### 1) Clone and enter the repository

```bash
git clone <your-repo-url> qnaforum
cd qnaforum
```

### 2) Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -U pip
pip install .
```

### 4) Configure environment

Copy and adjust defaults as needed:

```bash
cp .env.example .env
```

Default values:

- `QNA_DATABASE_URL=sqlite:///./data/qna.db`
- `QNA_FAISS_INDEX_PATH=data/faiss/qna.index`
- `QNA_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`

## Initialize the Portal

Run DB and seed scripts:

```bash
python -m app.scripts.init_db
python -m app.scripts.seed_demo_data
```

The seed command creates an `admin` user and prints an admin API key once.

## Run the Service

### Development

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t qnaforum:latest .
docker run --rm -p 8000:8000 qnaforum:latest
```

## How to Use the UI

### Public read-only UI

- `/` — recent problems
- `/search?q=<query>` — search page
- `/problems/{external_id}` — problem detail + answers

### Admin UI

- `/admin` — dashboard
- `/admin/users` — list/create users
- `/admin/users/{id}` — issue API key for a user
- `/admin/audit` — view recent audit events

> MVP note: Admin actions are intentionally UI-only. There is no admin API.

## How to Use the API

API base: `http://localhost:8000/api/v1`

Auth for write endpoints:

```http
Authorization: Bearer <api_key>
```

### Health

```bash
curl http://localhost:8000/api/v1/health
```

### Create a problem

```bash
curl -X POST http://localhost:8000/api/v1/problems \
  -H "Authorization: Bearer $QNA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "How do I persist a FAISS index?",
    "body_markdown": "I am building a local demo app...",
    "tags": ["faiss", "search", "python"]
  }'
```

### Add an answer

```bash
curl -X POST http://localhost:8000/api/v1/problems/Q-000001/answers \
  -H "Authorization: Bearer $QNA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"body_markdown":"Use faiss.write_index(...) on shutdown","kind":"solution"}'
```

### Search

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"persist faiss index","mode":"hybrid","top_k":10}'
```

Search modes:

- `keyword` (FTS5)
- `semantic` (FAISS)
- `hybrid` (combined)

## How to Use the CLI

The package installs a `qna` command.

Set defaults:

```bash
export QNA_BASE_URL=http://localhost:8000
export QNA_API_KEY=<your_api_key>
```

### Search

```bash
qna search "persist faiss index" --mode hybrid
qna search "E_CONNRESET" --mode keyword --json
```

### Create and show problem

```bash
cat > question.md <<'MD'
How can I rotate API keys without downtime?
MD

qna problem create \
  --title "How can I rotate API keys without downtime?" \
  --body-file question.md \
  --tags auth,api,security

qna problem show Q-000001 --json
```

### Create answer

```bash
cat > answer.md <<'MD'
Use staged rotation with overlap and revoke old keys after confirmation.
MD

qna answer create Q-000001 --body-file answer.md --kind solution
```

## FAISS Rebuild (from SQLite)

Recreate vector index from active search documents:

```bash
python -m app.scripts.rebuild_faiss
```

This is the recovery path if vector index and SQLite drift.

## Running Tests

```bash
pytest -q
```

Integration tests live in `app/tests/test_integration.py` and cover major API/admin flows.
