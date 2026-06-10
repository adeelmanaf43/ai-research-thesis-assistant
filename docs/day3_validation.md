# Week 1 Day 3 Validation

Day 3 added the Project CRUD API foundation.

## Completed Scope

- Project service layer for create, list, get, update, and delete operations
- FastAPI project routes mounted under `/api/projects`
- Project request and response schemas with blank title validation
- API route tests using temporary SQLite databases
- API documentation and README examples for manual verification

## Validation Commands

Run from the project root after activating the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_project_service.py
.\.venv\Scripts\python.exe -m pytest backend\tests\test_project_routes.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Expected result:

```text
All tests pass.
All lint checks pass.
```

## Manual API Check

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Create a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Expected result:

```text
StatusCode: 201
```

List projects:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Expected result:

```text
StatusCode: 200
```

## Known Day 3 Boundaries

- No document upload yet
- No PDF extraction yet
- No search, retrieval, LLM, Ollama, cloud provider, export, auth, or payment features yet
- Project ownership is modeled for future use, but login is intentionally not required in the MVP foundation
