# Project Roadmap

This roadmap keeps the AI Research / Thesis Assistant local-first, lightweight, and portfolio-ready. Each milestone should produce working code, tests, and documentation before moving to the next layer.

## Week 1: Professional Project Foundation

Goal: create a clean, testable, documented base that can be committed and tagged.

- Day 1: repository structure, environment files, backend/frontend/docs folders, README skeleton, and roadmap
- Day 2: backend app factory, configuration loading, and health endpoint
- Day 3: SQLite foundation and initial persistence boundaries
- Day 4: Streamlit frontend shell and local developer workflow
- Day 5: testing, documentation pass, milestone review, commit, and tag

## Week 2: Document Intake Foundation

Goal: add local project and document intake without AI dependencies.

- Project creation
- Local file upload flow
- Safe file naming and storage rules
- Basic document metadata
- Empty or unsupported file warnings

## Week 3: Local Text Processing

Goal: make documents useful with deterministic local processing.

- PDF text extraction
- Text cleaning
- Section detection
- Chunking with overlap
- Word count and page count

## Week 4: Local Analysis

Goal: produce helpful outputs without LLMs.

- Keyword extraction
- Extractive summaries
- Reference detection
- Research information extraction
- Literature matrix draft data

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

