# Day 2 Validation

Week 1, Day 2 confirms the backend configuration and database base are ready for the next milestone.

## Validation Commands

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_config.py backend/tests/test_database.py backend/tests/test_models.py backend/tests/test_schemas.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Manual database check:

```powershell
.\.venv\Scripts\python.exe -c "from sqlalchemy import inspect; from backend.app.core.database import engine, init_database; init_database(); print(sorted(inspect(engine).get_table_names()))"
```

Expected table list:

```text
['analyses', 'chat_history', 'chunks', 'documents', 'projects', 'users']
```

## Verified Scope

- Settings load defaults and environment overrides.
- Relative paths resolve from the project root.
- Invalid non-SQLite database URLs fail clearly.
- Upload and export directories are created locally.
- SQLAlchemy engine and session factory work with SQLite.
- `init_database()` creates the base ORM tables.
- Project and document response schemas avoid exposing internal storage paths.
- The MVP can create a project/document graph without login.
- No paid API key, cloud provider, mandatory Ollama, Docker, auth, or payment dependency is required.

## Commit Checklist

Before committing:

```powershell
git status
git check-ignore -v .env
git check-ignore -v .venv/
git check-ignore -v data/app.db
git add .
git diff --cached --name-only
git commit -m "Week 1 Day 2 backend config and database base"
git tag week-1-day-2-backend-config-db
```

If Git reports dubious ownership on Windows, run this once with your actual local project path:

```powershell
git config --global --add safe.directory "<absolute-project-path>"
```

