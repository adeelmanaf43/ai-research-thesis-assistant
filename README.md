# AI Research / Thesis Assistant

A local-first document intelligence web app for students, researchers, thesis writers, academic freelancers, and analysts.

The project is designed to keep working without paid APIs, mandatory Ollama, or cloud services. Week 1 focuses on a professional project foundation: clean structure, configuration, tests, documentation, and a minimal working app skeleton.

## Current Milestone

Week 1, Day 1: Repository, environment, and project skeleton.

Included now:

- FastAPI backend skeleton with health endpoints
- Streamlit frontend skeleton
- Local configuration using environment variables
- SQLite connection helper
- Pytest setup and foundation tests
- Documentation starter set

Not included yet:

- PDF extraction
- LLM providers
- RAG/retrieval
- Report export
- Authentication
- Payments
- Docker
- Cloud AI APIs

## Quick Start

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

Run the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Backend-only dependencies are listed in `backend/requirements.txt`.

Run the frontend:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/streamlit_app.py
```

## Project Structure

```text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
  tests/
frontend/
  pages/
docs/
sample_data/
data/
```

See [project-roadmap.md](project-roadmap.md), [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), and [docs/day1_validation.md](docs/day1_validation.md) for more detail.
