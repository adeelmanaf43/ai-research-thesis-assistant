# Architecture Notes

The product is local-first. The system must remain useful when Ollama is unavailable, no paid API key exists, documents are long, or local hardware is limited.

## Current Layers

- `backend/app/main.py`: FastAPI application factory and route registration
- `backend/app/core/config.py`: environment-driven local configuration
- `backend/app/core/database.py`: SQLite connection helper
- `backend/app/api/`: HTTP routes
- `backend/app/schemas/`: API response/request schemas
- `backend/app/models/`: future persistence models
- `backend/app/services/`: future document intelligence services
- `frontend/streamlit_app.py`: Streamlit entry point

## Planned Local-First Flow

Project creation, file upload, text extraction, cleaning, section detection, chunking, local overview, source-grounded Q&A, comparison, and export will be added in later milestones.

Ollama and cloud providers are optional layers behind provider abstractions. They must never be required for the core app to work.

