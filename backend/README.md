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
