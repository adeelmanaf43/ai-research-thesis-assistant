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

## Project API Examples

Create a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Expected response status: `201 Created`.

List projects:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Expected response status: `200 OK`.

Get one project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1"
```

Update a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Patch -ContentType "application/json" -Body '{"name":"Updated thesis project"}'
```

Delete a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Delete
```

Expected delete response status: `204 No Content`.

## Run Tests

```powershell
python -m pytest backend/tests/test_health_api.py
python -m pytest backend/tests/test_project_routes.py
python -m pytest backend/tests/test_document_routes.py
python -m pytest
```

The health endpoint test uses `httpx` against the FastAPI ASGI app directly, so it does not need a running server.

Project CRUD API tests also use `httpx` against an in-memory ASGI client, but they override the database dependency with a temporary SQLite database under `data/test_tmp`. They do not write project test records into the real local database at `data/app.db`.

## Quality Checks

```powershell
python -m ruff check .
python -m black --check --workers 1 backend frontend
```

Format Python files:

```powershell
python -m black --workers 1 backend frontend
```

## Document Storage Foundation

Document files will be stored under the configured `UPLOAD_DIR` using this project-scoped structure:

```text
uploads/
  projects/
    {project_id}/
      documents/
        {stored_filename}
```

Hour 1 of Day 4 adds path helper functions in `backend/app/services/document_storage.py`.

- `sanitize_upload_filename()` removes path components and unsafe filename characters.
- `build_stored_document_filename()` adds a unique safe prefix to an original filename.
- `get_project_documents_dir()` resolves `uploads/projects/{project_id}/documents/`.
- `ensure_project_documents_dir()` creates the project document directory when needed.
- `get_document_storage_path()` returns a safe path inside the project document directory.

These helpers do not upload, parse, or extract PDF content yet. They only establish the safe local storage boundary for later document upload work.

## Document Service Foundation

Hour 2 of Day 4 adds document service functions in `backend/app/services/document_service.py`.

- `save_uploaded_file()` writes provided file bytes to the safe project document directory.
- `create_document_record()` creates the database row for a saved document file.
- `update_document_status()` updates document workflow status and rejects blank statuses.
- `list_documents_by_project()` returns documents scoped to one project.

These functions are service-layer building blocks used by the document upload API. PDF extraction, text parsing, and analysis workflows are still outside this milestone.

## Document Upload API

Hour 3 of Day 4 adds a PDF-only upload endpoint:

```text
POST /api/projects/{project_id}/documents
```

Manual example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\example.pdf;type=application/pdf"
```

Expected response status: `201 Created`.

Upload validation:

- The project must exist.
- The uploaded filename must end in `.pdf`.
- When a content type is provided, it must be `application/pdf` or `application/x-pdf`.
- File bytes must not exceed `MAX_UPLOAD_FILE_SIZE_BYTES`.

This endpoint stores the PDF file locally and creates a document metadata row. It does not extract text, count pages, summarize, or call any AI provider yet.

Upload validation tests use small fake file bytes. They verify routing, validation, local saving, and metadata creation only; they intentionally do not parse PDF content.

Security notes:

- User-provided filenames are sanitized before storage.
- Uploaded files are resolved under `UPLOAD_DIR/projects/{project_id}/documents/`.
- Path traversal attempts such as `../../file.pdf` cannot escape the configured upload directory.
- API responses intentionally exclude internal storage fields such as `file_path` and `stored_filename`.
- Generated uploads under `data/uploads/` are ignored by Git so local user files are not committed accidentally.
- The upload endpoint stores bytes and metadata only; PDF parsing and malware scanning are outside the Week 1 milestone.

## Database Notes

The backend uses SQLAlchemy with SQLite for the local-first MVP.

- `backend/app/core/config.py` loads settings from environment variables and `.env`.
- `DATABASE_URL` defaults to `sqlite:///data/app.db`.
- `UPLOAD_DIR` defaults to `data/uploads`.
- `EXPORT_DIR` defaults to `data/exports`.
- `PROVIDER_MODE` defaults to `local`.
- `MAX_UPLOAD_FILE_SIZE_BYTES` defaults to `26214400`.
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
