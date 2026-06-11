# Week 1 Learning Notes

These notes explain what was built in Week 1 and how to discuss it in interviews.

## Product Foundation

The project is a local-first AI Research / Thesis Assistant. Week 1 focused on building a professional foundation instead of jumping straight to AI features.

The app can now:

- Start a FastAPI backend with health checks
- Start a Streamlit frontend skeleton
- Load local settings from environment variables
- Use SQLite through SQLAlchemy
- Create, list, view, update, and delete projects
- Store PDF uploads under project-scoped local directories
- Create document metadata records
- Run tests, lint checks, and formatting checks

## Local-First Design

The most important Week 1 decision is that the app works without paid APIs, cloud services, Docker, mandatory Ollama, or authentication.

Interview explanation:

> I designed the foundation so the core product remains useful on a local machine. AI providers can be added later, but project management, file storage, metadata, tests, and documentation already work without external services.

Why it matters:

- Students and researchers can use the product without cloud costs.
- Local storage keeps early document handling simple and inspectable.
- The system can fail gracefully when optional AI layers are unavailable.

## Backend Architecture

The backend uses FastAPI with clear separation of concerns.

- API routes handle HTTP concerns.
- Schemas define request and response contracts.
- Services contain business logic.
- Models define database tables.
- Core modules own configuration and database setup.

Interview explanation:

> I kept business logic out of route handlers. Routes validate HTTP inputs and delegate to service functions. That makes the system easier to test, easier to refactor, and safer to extend when document extraction and AI workflows are added later.

## Database Foundation

SQLite is used for the Week 1 MVP because it is local-first and simple to run.

Created base models:

- `User`
- `Project`
- `Document`
- `Chunk`
- `Analysis`
- `ChatHistory`

Project ownership is optional so the MVP can work without login.

Interview explanation:

> I modeled future product concepts early, but avoided building auth or advanced workflows before they were needed. This gives the app a realistic domain structure without overcomplicating the MVP.

## Project CRUD API

The Project API supports create, list, get, update, and delete operations.

Key design choices:

- Project logic lives in `project_service.py`.
- Pydantic schemas validate blank project names.
- API tests use temporary SQLite databases.
- Routes return clean response schemas.

Interview explanation:

> I used a service layer so CRUD behavior is testable without going through HTTP, while still adding endpoint tests to verify the FastAPI integration.

## Document Storage Foundation

Documents are stored under:

```text
uploads/projects/{project_id}/documents/
```

The storage helpers sanitize filenames and check resolved paths so uploads cannot escape the configured upload directory.

Interview explanation:

> Before building extraction, I built safe file storage. User filenames are not trusted, path traversal is blocked, and internal storage paths are not exposed in API responses.

Why it matters:

- File upload features are security-sensitive.
- Safe path handling prevents accidental writes outside local storage.
- Metadata can be stored without exposing implementation details.

## PDF Upload API

The upload route accepts PDFs only:

```text
POST /api/projects/{project_id}/documents
```

Validation includes:

- Project existence
- `.pdf` extension
- PDF content type when provided
- Configured file size limit

The route stores bytes and creates metadata only. It does not extract text, count pages, summarize, or call AI providers yet.

Interview explanation:

> I intentionally separated upload and metadata from PDF extraction. That keeps the first milestone reliable and testable before adding more complex parsing logic.

## Testing Strategy

Week 1 tests cover:

- Project structure
- Configuration loading
- Database initialization
- ORM model registration
- Project service and routes
- Document storage helpers
- Document service functions
- Document upload route validation
- Schema serialization boundaries
- Tooling configuration

Important testing pattern:

> API tests override database dependencies with temporary SQLite databases so tests do not pollute the real local database.

Why it matters:

- Tests are repeatable.
- Local data is protected.
- Features can be changed safely.

## Documentation Strategy

Documentation was updated as features were added.

Key docs:

- `README.md`: project overview and quick start
- `backend/README.md`: backend commands and API notes
- `docs/api.md`: endpoint list and examples
- `docs/architecture.md`: architecture decisions
- `docs/setup.md`: setup and quality commands
- `docs/day*_validation.md`: milestone validation records

Interview explanation:

> I treated documentation as part of the product, not an afterthought. Each milestone records what works, what is intentionally out of scope, and how to validate it.

## Quality Baseline

Development tooling now includes:

- `pytest` for tests
- `ruff` for linting
- `black` for formatting

Interview explanation:

> I added lightweight quality tooling once the foundation had enough code to benefit from it. The goal was consistency and maintainability without adding unnecessary process overhead.

## What Was Intentionally Not Built

Week 1 intentionally does not include:

- PDF text extraction
- OCR
- RAG or retrieval
- Local LLM calls
- Cloud AI APIs
- Authentication
- Payments
- Docker

Interview explanation:

> I avoided fake features. Week 1 builds a reliable foundation that can be demonstrated, tested, and extended. AI features will sit on top of this foundation later.

## Strong Interview Summary

Use this concise explanation:

> In Week 1, I built the professional foundation for a local-first AI Research / Thesis Assistant. The backend uses FastAPI, SQLite, SQLAlchemy, Pydantic schemas, and a service-layer architecture. It supports project CRUD and PDF upload metadata storage with safe local file paths. I added isolated tests, documentation, and quality tooling with Ruff and Black. I intentionally avoided AI and PDF extraction until the storage, API, database, and testing foundation were reliable.
