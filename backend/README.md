# Backend

FastAPI backend foundation for the AI Research / Thesis Assistant.

This backend is local-first. It uses SQLite-ready configuration and does not require paid API keys, cloud providers, Ollama, Docker, authentication, or payment services for the Week 1 foundation.

## Create Virtual Environment

Open PowerShell in the project root, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install Requirements

For backend runtime only:

```powershell
pip install -r backend/requirements.txt
```

For backend development and tests:

```powershell
pip install -r requirements-dev.txt
```

## Run Server

```powershell
python -m uvicorn backend.app.main:app --reload
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "environment": "local",
  "mode": "local-first"
}
```

## Run Tests

```powershell
python -m pytest backend/tests/test_health_api.py
python -m pytest
```

The health endpoint test uses `httpx` against the FastAPI ASGI app directly, so it does not need a running server.

## Database Notes

The backend uses SQLAlchemy with SQLite for the local-first MVP.

- `backend/app/core/config.py` loads settings from environment variables and `.env`.
- `DATABASE_URL` defaults to `sqlite:///data/app.db`.
- `UPLOAD_DIR` defaults to `data/uploads`.
- `EXPORT_DIR` defaults to `data/exports`.
- `PROVIDER_MODE` defaults to `local`.
- `backend/app/core/database.py` exposes `engine`, `SessionLocal`, `get_db()`, `Base`, and `init_database()`.
- Base ORM tables are `users`, `projects`, `documents`, `chunks`, `analyses`, and `chat_history`.
- `Project.user_id` is nullable so the MVP can work without login.

Initialize the local database tables:

```powershell
python -c "from backend.app.core.database import init_database; init_database(); print('database-ready')"
```

Inspect the created tables:

```powershell
python -c "from sqlalchemy import inspect; from backend.app.core.database import engine, init_database; init_database(); print(sorted(inspect(engine).get_table_names()))"
```
