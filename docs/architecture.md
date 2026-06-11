# Architecture Notes

The product is local-first. The system must remain useful when Ollama is unavailable, no paid API key exists, documents are long, or local hardware is limited.

## Current Layers

- `backend/app/main.py`: FastAPI application factory and route registration
- `backend/app/core/config.py`: environment-driven local configuration
- `backend/app/core/database.py`: SQLAlchemy SQLite engine, session dependency, declarative `Base`, and metadata initialization utility
- `backend/app/api/`: HTTP routes
- `backend/app/schemas/`: API response/request schemas
- `backend/app/models/`: base ORM models for users, projects, documents, chunks, analyses, and chat history
- `backend/app/services/`: business logic services kept outside API route modules
- `frontend/streamlit_app.py`: Streamlit entry point

## Planned Local-First Flow

Project creation, file upload, text extraction, cleaning, section detection, chunking, local overview, source-grounded Q&A, comparison, and export will be added in later milestones.

Ollama and cloud providers are optional layers behind provider abstractions. They must never be required for the core app to work.

## Configuration Defaults

The backend loads local settings from environment variables and `.env` when available. Relative local paths are resolved from the project root so commands work consistently from the repository. The default provider mode is `local`, and the app creates upload/export directories on startup.

## Database Foundation

The backend uses SQLAlchemy with SQLite for the local-first MVP. `backend/app/core/database.py` exposes the shared engine, `SessionLocal`, `get_db()` FastAPI dependency, declarative `Base`, and `init_database()` utility.

The Week 1 foundation includes base ORM tables for `User`, `Project`, `Document`, `Chunk`, `Analysis`, and `ChatHistory`. User ownership is optional on projects so the MVP can work without a login flow.

## Schema Boundary

Project and document Pydantic schemas provide serialization-friendly request and response contracts. Document responses intentionally omit internal storage fields such as `file_path` and `stored_filename`.

Project schemas separate creation/update input from list/detail responses and reject blank project names.

## Service Layer

Project CRUD behavior starts in `backend/app/services/project_service.py`. Routes should call service functions instead of placing database business logic directly in API modules.

Document storage path behavior starts in `backend/app/services/document_storage.py`. File storage helpers keep uploaded document paths inside the configured upload directory and use the structure `uploads/projects/{project_id}/documents/`.

Document persistence behavior starts in `backend/app/services/document_service.py`. It provides service-layer functions for saving supplied file bytes, creating document database records, updating document status, and fetching documents by project.

## Project API

Project routes live in `backend/app/api/routes_projects.py` and are mounted under `/api/projects`. They remain thin FastAPI handlers over the project service layer.

## Document API

Document upload routes live in `backend/app/api/routes_documents.py` and are mounted under `/api/projects/{project_id}/documents`. The upload route validates project existence, PDF extension, provided content type, and configured file size before calling document services.

## Document Storage Boundary

The storage foundation defines safe local path helpers used by the upload endpoint. Filenames are sanitized before storage, project IDs must be positive integers, and resolved paths are checked so path traversal cannot escape the configured upload directory.

The document upload API can save PDF bytes and create document metadata records, but it does not extract text, count pages, or run analysis yet.
