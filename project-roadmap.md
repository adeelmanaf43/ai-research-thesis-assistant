# Project Roadmap

This roadmap keeps the AI Research / Thesis Assistant local-first, lightweight, and portfolio-ready. Each milestone should produce working code, tests, and documentation before moving to the next layer.

## Week 1: Professional Project Foundation

Goal: create a clean, testable, documented base that can be committed and tagged.

- Day 1: repository structure, environment files, backend/frontend/docs folders, README skeleton, roadmap, backend skeleton, health endpoint, Streamlit shell, and pytest baseline
- Day 2: robust settings management, SQLAlchemy SQLite foundation, base ORM models, and starter schemas
- Day 3: project CRUD service layer, FastAPI project routes, validation schemas, API tests, and endpoint documentation
- Day 4: safe document storage helpers, document service foundation, PDF-only upload API, upload validation tests, and storage security notes
- Day 5: development tooling, quality commands, learning notes, portfolio README, validation review, commit, and tag

## Week 2: PDF Extraction, Cleaning, and Processing Pipeline

Goal: build reliable local document ingestion without AI dependencies.

- PDF text extraction
- Text cleaning
- Empty or scanned document warnings
- Section detection
- Chunking with overlap
- Store processing metadata for later retrieval

## Week 3: Local Analysis Foundation

Goal: make processed documents useful with deterministic local analysis.

- Keyword extraction
- Extractive summaries
- Reference detection
- Research information extraction

## Week 4: Literature Review Outputs

Goal: turn deterministic analysis into structured research workspace data.

- Literature matrix draft data
- Multi-paper comparison inputs
- Citation/reference review helpers
- Research notes suitable for later report export

## Week 5: Search and Source-Grounded Q&A

Goal: support reliable search and answers based on stored document chunks.

- TF-IDF search
- Retrieved source chunks
- Local fallback answer generation
- Clear citations to source snippets

## Week 6: Optional Provider Layer

Goal: add optional enhancement providers without making them required.

- Provider base interface
- Local provider
- Ollama provider with strict context limits, timeouts, and fallback
- Cloud provider stubs without required paid keys

## Week 7: Reports and Comparison

Goal: turn analysis into professional deliverables.

- Multi-paper comparison
- Literature review matrix
- Markdown export
- DOCX export
- PDF export if local dependencies support it safely

## Week 8: Portfolio Polish

Goal: make the project easy to demo, explain, and maintain.

- Usage guide
- Architecture notes
- Known limitations
- Demo data
- Final test pass
- Recruiter-readable README

## Guardrails

- Local processing must work first.
- Ollama is optional and must never receive full papers or long chapters.
- Cloud providers are future optional layers.
- No hardcoded secrets.
- No auth, payments, Docker, or SaaS complexity in the MVP.
- Every meaningful feature needs tests and documentation.
