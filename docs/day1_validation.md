# Day 1 Validation

Week 1, Day 1 confirms the repository, environment, backend skeleton, frontend skeleton, tests, and documentation foundation are ready for a first milestone commit.

## Validation Commands

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Manual health check:

```text
http://127.0.0.1:8000/health
```

Expected health response:

```json
{
  "status": "ok",
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "environment": "local",
  "mode": "local-first"
}
```

## Verified Scope

- Root repository structure exists.
- Backend FastAPI app imports successfully.
- Health endpoints are registered.
- Streamlit frontend skeleton exists.
- Pytest runs from the project virtual environment.
- Ruff passes.
- No paid API key, cloud provider, mandatory Ollama, Docker, auth, or payment dependency is required.

## Commit Checklist

Before committing:

```powershell
git status
git check-ignore -v .env
git check-ignore -v .venv/
git add .
git diff --cached --name-only
git commit -m "Week 1 Day 1 project foundation"
git tag week-1-day-1-foundation
```

If Git reports dubious ownership on Windows, run this once with your actual local project path:

```powershell
git config --global --add safe.directory "<absolute-project-path>"
```
