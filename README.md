# AI Research / Thesis Assistant

A local-first document intelligence web app for students, researchers, thesis writers, academic freelancers, and analysts.

The project is designed to keep working without paid APIs, mandatory Ollama, or cloud services. The current foundation includes project management, safe PDF upload, local PDF text extraction, tests, and documentation.

## Problem

Research and thesis workflows often spread across PDFs, notes, spreadsheets, chat tools, and manual summaries. Many AI document tools also assume cloud uploads, paid API keys, or large model availability before the core workflow is useful.

This project addresses that gap by building a local-first assistant that can manage research projects and document intake before optional AI layers are added.

## Solution

AI Research / Thesis Assistant is being built as a local document intelligence app. The first milestone focuses on reliable foundations:

- Create and manage research projects
- Upload PDF documents safely into project-scoped local storage
- Store document metadata in SQLite
- Keep business logic testable through service layers
- Add deterministic tests, documentation, linting, and formatting

Future milestones will add text cleaning, chunking, search, source-grounded Q&A, literature matrices, comparison, and report export.

## Architecture

The app uses a modular FastAPI backend and a Streamlit frontend shell.

```text
backend/
  app/
    api/          HTTP route modules
    core/         configuration and database setup
    models/       SQLAlchemy ORM models
    schemas/      Pydantic request and response contracts
    services/     business logic and storage helpers
  tests/          pytest suite
frontend/
  streamlit_app.py
docs/
sample_data/
data/
```

Important boundaries:

- API routes handle HTTP concerns.
- Services handle business logic.
- Schemas define public API contracts.
- Models define persistence.
- Local files stay under `data/uploads/`.

## Tech Stack

- Python
- FastAPI
- Streamlit
- SQLite
- SQLAlchemy
- PyMuPDF
- Pydantic
- Pytest
- Ruff
- Black

No Docker, paid API key, cloud provider, auth system, or payment layer is required for the current local-first foundation.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run quality checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
```

Format Python files:

```powershell
.\.venv\Scripts\python.exe -m black --workers 1 backend frontend
```

Run the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Run the frontend:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/streamlit_app.py
```

## Current Features

Week 2, Day 1: PDF text extraction service.

Included now:

- FastAPI backend skeleton with health endpoints
- Streamlit frontend skeleton
- Local configuration using environment variables
- SQLAlchemy SQLite database foundation
- Base ORM models for projects, documents, chunks, analyses, and chat history
- Pydantic schemas for project and document basics
- Project CRUD service layer and FastAPI routes
- Isolated API tests for project endpoints using temporary SQLite databases
- Safe document storage path helpers under `uploads/projects/{project_id}/documents/`
- Document service placeholders for saving files, creating records, status updates, and project-scoped document fetches
- PDF-only document upload API with project existence, extension, content type, and size validation
- Local PDF text extraction service using PyMuPDF
- Upload-time extraction metadata with page count, word count, `extracted`, `extraction_failed`, and `ocr_needed` statuses
- Ruff linting and Black formatting configuration
- Pytest setup and foundation tests
- Documentation starter set

Example project creation:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Example project listing:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Example PDF upload:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

## Roadmap

Near-term milestones:

- Local PDF text extraction
- Text cleaning
- Section detection
- Chunking with overlap
- Local summaries and keyword extraction
- TF-IDF search
- Source-grounded Q&A
- Literature review matrix
- Multi-paper comparison
- Markdown, DOCX, and PDF report export
- Optional Ollama provider with strict context limits and local fallback

See [project-roadmap.md](project-roadmap.md) for the full staged plan.

## Limitations

Not included yet:

- OCR processing for scanned PDFs
- Text cleaning
- Section detection
- Chunking
- LLM providers
- RAG/retrieval
- Report export
- Authentication
- Payments
- Docker
- Cloud AI APIs

The current upload API stores PDF bytes, creates document metadata, and attempts local PyMuPDF extraction to populate page count, word count, status, and extraction errors. It does not summarize or analyze document content yet.

## Screenshots

Screenshots will be added after the frontend has meaningful project and document workflows.

Planned placeholders:

- Backend health check
- Streamlit foundation screen
- Project list workflow
- PDF upload workflow

## Documentation

See [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), [docs/api-reference.md](docs/api-reference.md), [docs/weekly-progress.md](docs/weekly-progress.md), [docs/week2-day1-validation.md](docs/week2-day1-validation.md), [docs/learning-notes.md](docs/learning-notes.md), [docs/day1_validation.md](docs/day1_validation.md), [docs/day2_validation.md](docs/day2_validation.md), [docs/day3_validation.md](docs/day3_validation.md), [docs/day4_validation.md](docs/day4_validation.md), and [docs/day5_validation.md](docs/day5_validation.md) for more detail.
