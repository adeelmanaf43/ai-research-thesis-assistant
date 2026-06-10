# Architecture Notes

The product is local-first. The system must remain useful when Ollama is unavailable, no paid API key exists, documents are long, or local hardware is limited.

## Current Layers

- `backend/app/main.py`: FastAPI application factory and route registration
- `backend/app/core/config.py`: environment-driven local configuration
- `backend/app/core/database.py`: SQLAlchemy SQLite engine, session dependency, declarative `Base`, and metadata initialization utility
- `backend/app/api/`: HTTP routes
- `backend/app/schemas/`: API response/request schemas
- `backend/app/models/`: base ORM models for users, projects, documents, chunks, analyses, and chat history
- `backend/app/services/`: future document intelligence services
- `frontend/streamlit_app.py`: Streamlit entry point

## Planned Local-First Flow

Project creation, file upload, text extraction, cleaning, section detection, chunking, local overview, source-grounded Q&A, comparison, and export will be added in later milestones.

Ollama and cloud providers are optional layers behind provider abstractions. They must never be required for the core app to work.

## Configuration Defaults

The backend loads local settings from environment variables and `.env` when available. Relative local paths are resolved from the project root so commands work consistently from the repository. The default provider mode is `local`, and the app creates upload/export directories on startup.

## Database Foundation

The backend uses SQLAlchemy with SQLite for the local-first MVP. `backend/app/core/database.py` exposes the shared engine, `SessionLocal`, `get_db()` FastAPI dependency, declarative `Base`, and `init_database()` utility.

Hour 3 adds base ORM tables for `User`, `Project`, `Document`, `Chunk`, `Analysis`, and `ChatHistory`. User ownership is optional on projects so the MVP can work without a login flow.

## Schema Boundary

Project and document Pydantic schemas provide serialization-friendly request and response contracts. Document responses intentionally omit internal storage fields such as `file_path` and `stored_filename`.
