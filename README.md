# AI Research / Thesis Assistant

A local-first document intelligence web app for students, researchers, thesis writers, academic freelancers, and analysts.

The project is designed to keep working without paid APIs, mandatory Ollama, or cloud services. The current foundation includes project management, safe PDF upload, local PDF text extraction, deterministic text cleaning, local keyword/statistics analysis, extractive section summaries, tests, and documentation.

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

Future milestones will add chunking, search, source-grounded Q&A, literature matrices, comparison, and report export.

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

Week 4, Day 1: Provider abstraction and local provider implementation.

Included now:

- FastAPI backend skeleton with health endpoints
- Streamlit frontend shell with optional backend document overview and section summary lookup
- Local configuration using environment variables
- SQLAlchemy SQLite database foundation
- Base ORM models for projects, documents, chunks, analyses, and chat history
- Pydantic schemas for project and document basics
- Project CRUD service layer and FastAPI routes
- Isolated API tests for project endpoints using temporary SQLite databases
- Safe document storage path helpers under `uploads/projects/{project_id}/documents/`
- Document service functions for saving files, creating records, status updates, and project-scoped document fetches
- PDF-only document upload API with project existence, extension, content type, and size validation
- Local PDF text extraction service using PyMuPDF
- Upload-time processing metadata with page count, word count, `processed`, `extraction_failed`, `ocr_needed`, and processing failure statuses
- Deterministic text cleaning pipeline with original text, cleaned text, cleaning statistics, and warnings
- Internal extracted-text and cleaned-text artifacts saved beside uploaded PDFs for later pipeline stages
- Rule-based section detection service with structured section names, headings, indexes, text, confidence, and unknown fallbacks
- Internal section_detection analysis output stored after successful upload processing
- Chunking service foundation for cleaned text or detected section text using 500-800 word chunks and 100-150 word overlap
- Transactional chunk replacement service that clears stale document chunks before inserting reprocessed chunks
- Processed document lifecycle documented from upload through chunk persistence
- Document overview API with filename, status, page count, word count, chunk count, detected sections, warnings, and structured processing summary
- Local keyword extraction with stopword filtering, deterministic scores, and frequencies
- Local document statistics with word count by section, chunk count by section, reference count estimate, and basic readability metrics
- Local overview analysis storage using `analysis_type="document_overview_local"`
- API endpoints to generate and fetch stored local overview analysis
- Local extractive section summaries for abstract, introduction, methodology, results, discussion, and conclusion sections
- Local section summary analysis storage using `analysis_type="section_summaries_local"` and `provider_mode="local"`
- Local research information extraction storage using `analysis_type="research_info_local"` and `provider_mode="local"`
- Service-level TF-IDF retrieval over stored chunks with document filtering and source chunk metadata
- Local document search endpoint with preview-first retrieval results
- Local extractive Q&A fallback that answers only from retrieved source chunks
- Local document chat endpoint that stores `ChatHistory` with `provider_mode="local"`
- Base LLM provider interface and factory with local default and safe future Ollama fallback
- Project-scoped document listing endpoint that hides internal storage paths
- Streamlit document overview panel that loads backend overview and section summary data when FastAPI is running
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

Example document overview:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/overview"
```

Example local overview analysis:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/local-overview" -Method Post
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/local-overview"
```

Example section summaries:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/summaries/sections"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/section-summaries" -Method Post
```

Example research information extraction:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/analysis/1/research-info" -Method Post
```

Local research information extraction is reliable for clear academic writing patterns, but it is intentionally limited. It can extract common fields such as objectives, methods, samples, findings, limitations, and future work without Ollama or cloud APIs. It does not infer hidden meaning from vague prose, and it returns missing fields honestly as `null` with `0.0` confidence.

Example local document search:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/search?q=methodology%20sample&top_k=3"
```

Example local document chat:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/chat" -Method Post -ContentType "application/json" -Body '{"question":"What sample did the methodology use?","top_k":3}'
```

The Streamlit frontend can load the document overview, section summaries, local search results, and source-grounded Q&A fallback when the backend is running. Use the default backend URL or set `THESIS_ASSISTANT_BACKEND_URL` before launching Streamlit.

## Roadmap

Near-term milestones:

- Public chunk API responses
- Full frontend project and upload workflow
- Richer frontend project and upload workflow
- Literature review matrix
- Multi-paper comparison
- Markdown, DOCX, and PDF report export
- Optional Ollama provider with strict context limits and local fallback

See [project-roadmap.md](project-roadmap.md) for the full staged plan.

## Limitations

Not included yet:

- OCR processing for scanned PDFs
- Public API access to stored cleaned text records
- Public API access to raw chunk records
- Perfect section detection for unusual headings or damaged PDF extraction output
- Public chunk API responses
- Full frontend display for all local analysis output
- Generative summaries or rewritten prose
- External LLM providers such as Ollama or cloud APIs
- RAG and source-grounded answer generation
- Report export
- Authentication
- Payments
- Docker
- Cloud AI APIs

The current upload API stores PDF bytes, creates document metadata, attempts local PyMuPDF extraction, runs deterministic text cleaning, saves internal raw/cleaned text artifacts, stores detected sections as local analysis output, and persists internal chunks after successful section detection. The local overview analysis API can generate and store deterministic keyword/statistics output from processed documents. Section summaries are extractive and select source sentences from detected sections rather than generating new prose, and they can be saved as local analysis output with `provider_mode="local"`. Section detection, keyword extraction, reference counting, readability metrics, and extractive summaries are rule-based and explainable, not replacements for semantic document understanding. The app does not use external or generative AI providers yet.

## Screenshots

Screenshots will be added after the frontend has meaningful project and document workflows.

Planned placeholders:

- Backend health check
- Streamlit foundation screen
- Project list workflow
- PDF upload workflow
- Document overview workflow

## Documentation

See [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), [docs/provider-architecture.md](docs/provider-architecture.md), [docs/api.md](docs/api.md), [docs/api-reference.md](docs/api-reference.md), [docs/week-02-demo.md](docs/week-02-demo.md), [docs/week-03-demo.md](docs/week-03-demo.md), [docs/weekly-progress.md](docs/weekly-progress.md), [docs/week2-day1-validation.md](docs/week2-day1-validation.md), [docs/week2-day6-validation.md](docs/week2-day6-validation.md), [docs/learning-notes.md](docs/learning-notes.md), [docs/day1_validation.md](docs/day1_validation.md), [docs/day2_validation.md](docs/day2_validation.md), [docs/day3_validation.md](docs/day3_validation.md), [docs/day4_validation.md](docs/day4_validation.md), and [docs/day5_validation.md](docs/day5_validation.md) for more detail.
