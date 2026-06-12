# Next Steps

Week 1 established the professional project foundation: repository structure, FastAPI backend, Streamlit shell, local configuration, SQLite database setup, project CRUD, document upload storage, tests, documentation, and quality tooling.

Suggested Week 2 sequence:

1. Store extracted full text safely for later cleaning and chunking.
2. Add deterministic text cleaning helpers with focused tests.
3. Add section detection and chunking in service modules.
4. Add optional OCR processing later without making it required for the MVP.
5. Keep document processing in service modules so API routes stay thin.
