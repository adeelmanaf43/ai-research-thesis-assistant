# Week 1 Day 5 Validation

Day 5 closes the Week 1 development tooling and quality baseline. The milestone remains local-first and does not add PDF extraction, AI providers, authentication, payments, Docker, or cloud dependencies.

## Scope Validated

- Root README includes problem, solution, architecture, tech stack, setup, current features, roadmap, limitations, screenshots placeholder, and documentation links.
- Development tooling is configured with Ruff and Black.
- `requirements-dev.txt` includes the runtime dependencies plus test, lint, and format tools.
- `docs/learning-notes.md` explains Week 1 decisions in interview-ready language.
- Backend imports, route registration, tests, linting, and formatting were checked.

## Commands Run

```powershell
.\.venv\Scripts\python.exe -c "from backend.app.main import app; print(app.title); print(sorted(route.path for route in app.routes if route.path in {'/','/health','/api/v1/health'} or route.path.startswith('/api/projects')))"
.\.venv\Scripts\python.exe -c "from backend.app.core.config import get_settings; from backend.app.core.database import Base; from backend.app.services.document_service import save_uploaded_file; from backend.app.services.project_service import create_project; print(get_settings().provider_mode); print(Base.__name__); print('imports-ok')"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
$env:BLACK_CACHE_DIR='data/test_tmp/black_cache_day5_hour5'; .\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
git diff --check
```

## Expected Results

- Import checks print the application name, registered route paths, `local`, `Base`, and `imports-ok`.
- Pytest reports all tests passing.
- Ruff reports `All checks passed!`.
- Black reports all checked files would be left unchanged.
- `git diff --check` may report line-ending normalization warnings on Windows; it should not report whitespace errors.

## Manual Verification

1. Start the backend:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
   ```

2. Visit `http://127.0.0.1:8000/docs`.
3. Confirm health, project CRUD, and document upload endpoints are listed.
4. Open `README.md` and confirm it reads like a portfolio-ready project overview.
5. Open `docs/learning-notes.md` and confirm the architecture and testing decisions are explainable for interviews.

## Notes

- Generated app data remains under `data/` and is ignored by Git except for intentional `.gitkeep` files.
- Uploaded files remain local and project-scoped.
- The upload endpoint stores bytes and metadata only; document intelligence features start in later milestones.
