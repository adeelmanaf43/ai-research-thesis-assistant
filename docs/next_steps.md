# Next Steps

Week 1 established the professional project foundation: repository structure, FastAPI backend, Streamlit shell, local configuration, SQLite database setup, project CRUD, document upload storage, tests, documentation, and quality tooling.

Suggested Week 2 sequence:

1. Add local PDF text extraction without requiring Ollama or cloud APIs.
2. Detect empty or scanned PDFs and return clear user-facing warnings.
3. Store extracted document metadata such as page count and word count.
4. Add deterministic text cleaning helpers with focused tests.
5. Keep document processing in service modules so API routes stay thin.
