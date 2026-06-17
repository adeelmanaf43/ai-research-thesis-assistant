# Project Learning Notes

These notes explain what has been built so far and how to discuss the architecture, local-first decisions, and document processing pipeline in interviews.

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

## Week 2 Document Processing

Week 2 begins the local document intelligence pipeline. The app now extracts PDF text locally, cleans the extracted text deterministically, and stores separate text artifacts for later stages.

Current document processing flow:

- Upload and preserve the original PDF.
- Extract text locally with PyMuPDF.
- Detect empty or very low-text PDFs and mark them as `ocr_needed`.
- Run deterministic text cleaning after extraction.
- Save `.extracted.txt` and `.cleaned.txt` artifacts beside the uploaded PDF.
- Keep internal artifact paths out of public API responses.

Interview explanation:

> I split document processing into small local stages: upload, extraction, cleaning, and later chunking. Each stage has its own service and tests, which makes failures easier to debug and keeps the system useful without AI providers.

## Why Cleaning Comes Before Chunking

PDF extraction often produces text that looks readable to a human but is noisy for software. Common problems include broken academic paragraph lines, hyphenated words split across line breaks, repeated headers, page numbers, extra spaces, and control characters.

Cleaning before chunking matters because chunking turns text into the units that search, summaries, and Q&A will use later. If the input text is noisy, chunks become noisy too.

Examples:

- A word like `docu-\nment` should become `document` before chunking.
- Repeated page headers should not become highly ranked search terms.
- Page numbers should not appear as meaningful content.
- Broken lines should not split one academic idea into awkward fragments.
- Control characters should not pollute summaries or retrieval snippets.

Interview explanation:

> Cleaning is a quality gate before chunking. Chunking bad text produces bad retrieval and bad answers. By cleaning first, I improve the future search and AI layers without depending on an LLM to repair extraction noise.

## Why Cleaning Comes Before AI

AI providers are optional future enhancements in this project. The local system must remain useful even when Ollama is unavailable, a cloud API key is missing, or the machine is weak.

Cleaning before AI matters because:

- It reduces irrelevant tokens before any model call.
- It prevents repeated headers and page numbers from distracting summaries.
- It improves source-grounded answers by making retrieved context clearer.
- It lowers the chance that an AI model summarizes extraction artifacts instead of research content.
- It keeps the local-first pipeline valuable even without model access.

Interview explanation:

> I do not use AI as a cleanup shortcut. The app first builds a reliable deterministic text pipeline, then optional AI can work on cleaner, smaller, source-grounded context.

## Text Cleaning Testing Strategy

The text cleaning tests cover both cleanup and preservation.

Cleanup examples:

- Broken lines are repaired.
- Hyphenated line breaks are joined.
- Extra spaces are normalized.
- Page numbers are removed.
- Repeated short headers are removed.
- Strange control characters are removed.

Preservation examples:

- Academic punctuation is kept.
- Repeated meaningful findings are kept.
- The original PDF is not modified.
- Public API responses do not expose local text artifact paths.

Interview explanation:

> I tested the cleaner against realistic PDF extraction problems and also tested that it does not over-clean meaningful academic content. That balance matters because research tools must preserve source meaning.

## Rule-Based Section Detection

The section detection service identifies common academic sections using clear heading rules. It supports title, abstract, introduction, literature review, methodology, results, discussion, conclusion, references, and unknown fallbacks.

Why this matters:

- It gives later chunking and retrieval stages useful section metadata without requiring an LLM.
- It is deterministic, fast, local, and easy to test.
- It keeps unsupported headings in nearby section text instead of dropping source content.
- It records character indexes so later features can connect sections back to cleaned text.

Important limitation:

> Rule-based section detection is explainable but not semantically intelligent. It depends on extracted headings, so damaged PDF layout, unusual academic structure, OCR-only pages, or headings split across lines can reduce accuracy.

Interview explanation:

> I started with rule-based section detection because the MVP must work locally and predictably. It gives useful structure for later chunking while making limitations explicit. A future AI or ML layer can improve classification, but the deterministic baseline is already testable and inspectable.

## Local Keyword Extraction And Statistics

Week 3 starts the local intelligence layer. The keyword extractor uses simple tokenization, stopword filtering, frequency counts, and deterministic scoring. It is intentionally lightweight so the app remains useful without Ollama, cloud providers, or paid API keys.

The document statistics layer adds:

- Word count by detected section
- Chunk count by section
- Reference count estimate
- Basic readability-like metrics
- Stored local overview analysis under `analysis_type="document_overview_local"`

Why this matters:

- It makes processed PDFs useful before any LLM integration.
- It gives the future search and Q&A layers document-level signals.
- It keeps local analysis explainable and testable.
- It avoids pretending that approximate metrics are perfect semantic understanding.

Interview explanation:

> I added a deterministic local analysis layer before adding AI generation. It extracts keywords and document statistics from cleaned text, stores the result in SQLite, and exposes it through an API. This proves the product can provide useful document intelligence without relying on model availability or paid services.

## Local Research Information Extraction

The research information extractor uses local rules to find common academic signals such as research problem, objectives, research questions, methodology, dataset or sample, variables, findings, limitations, and future work. It works from cleaned text and stored section detection output when available.

Why this matters:

- It gives students and researchers a fast structured overview without requiring an LLM.
- It is deterministic, inspectable, and easy to test with known academic sample text.
- It stores `research_info_local` analysis records with `provider_mode="local"` so the source of the analysis is clear.
- It returns honest `null` values and `0.0` confidence when a field is not found instead of pretending every document contains every field.

Important limitation:

> Local extraction is reliable for clear academic writing patterns, but it is not semantic understanding. It can miss implied objectives, unusual methodology descriptions, merged PDF text, or findings written without recognizable keywords. These limits are acceptable for the local-first baseline because the behavior is transparent, testable, and safe to improve later with retrieval or optional AI providers.

Interview explanation:

> I built research information extraction locally before adding LLMs. The system can identify useful thesis fields using deterministic rules, store the result in SQLite, and explain confidence and missing fields honestly. This creates a dependable fallback layer that still works when model providers are unavailable.

## TF-IDF Retrieval Foundation

The retrieval service searches stored document chunks with local TF-IDF scoring. It uses scikit-learn, not an LLM, and returns source chunk metadata with each result.

Why this matters:

- It turns stored chunks into searchable evidence for later Q&A.
- It keeps retrieval local, deterministic, and testable.
- It supports document-level filtering so one paper can be searched independently from another.
- It uses preview-first response data so future endpoints can avoid returning full chunk text unless requested.
- It separates retrieval from answer generation, which keeps future source-grounded Q&A easier to reason about.

Why TF-IDF before FAISS or Chroma:

- It needs no embedding model and no vector index service.
- It is small enough for a local-first MVP and easy to run on weak machines.
- It gives deterministic test results, which is valuable before adding semantic retrieval.
- It creates a baseline that future FAISS, Chroma, or embedding search can be compared against.

Interview explanation:

> I added TF-IDF retrieval before FAISS or Chroma because the product first needs a dependable local baseline. TF-IDF works directly on stored chunks, requires no embedding model, and is easy to test. Later vector search can improve semantic matching, but it should be compared against this baseline instead of added as premature complexity.

## Local Source-Grounded Q&A Fallback

The local provider answers questions from retrieved chunks without calling an LLM. It selects source sentences that overlap with the question and returns those sentences as an extractive answer.

Why this matters:

- It prevents hallucination by refusing to answer when retrieved chunks do not contain the answer.
- It always returns source snippets so the user can inspect the evidence.
- It proves the product can support basic Q&A behavior without Ollama or cloud APIs.
- It creates a safe fallback for future provider chains.

Interview explanation:

> I implemented local Q&A as an extractive fallback, not a generator. The provider uses retrieved chunks, selects evidence sentences, and says when the answer is not found. That keeps the system honest and gives future LLM providers a reliable local backup.

## Week 3 Interview Notes: Local Intelligence System Design

Week 3 turns the document pipeline into a useful local intelligence system. The important architecture story is that each stage produces evidence for the next stage instead of depending on one large AI call.

System design flow:

```text
PDF upload -> extraction -> cleaning -> section detection -> chunking -> local analysis -> TF-IDF retrieval -> source-grounded Q&A fallback
```

Local-first design talking points:

- The app remains useful with no paid API key, no mandatory Ollama, and no cloud provider.
- SQLite stores projects, documents, chunks, analyses, and chat history locally.
- Deterministic services provide a reliable baseline before optional AI providers are introduced.
- Failure states are explicit: `ocr_needed`, `extraction_failed`, `chunking_failed`, or honest "answer not found" responses.
- The system avoids sending full papers to any provider, which protects privacy and reduces context-size risk.

Chunking talking points:

- Chunks are the bridge between long PDFs and useful local intelligence.
- Chunking happens after cleaning and section detection so each chunk has cleaner text and section metadata.
- Overlap protects context at chunk boundaries, which matters for search and Q&A.
- Stored chunk metadata includes chunk index, section name, approximate pages, text, and word count.
- Reprocessing deletes stale chunks and inserts fresh chunks transactionally so old evidence does not mix with new evidence.

Retrieval talking points:

- TF-IDF is the first retrieval layer because it is deterministic, local, lightweight, and easy to test.
- It works directly over stored SQLite chunks, so no embedding model or vector index server is required.
- The API returns source metadata, scores, previews, and optional full text.
- Phrase-aware TF-IDF with bigrams gives academic phrases a stronger signal while still staying simple.
- FAISS or Chroma can be added later, but only after measuring what TF-IDF cannot solve.

Fallback Q&A talking points:

- The local provider is intentionally extractive: it selects relevant source sentences instead of generating new prose.
- It returns source snippets with every answer so users can inspect evidence.
- It refuses to answer when retrieved chunks do not contain enough evidence.
- Chat history is persisted with `provider_mode="local"` so future provider comparisons remain auditable.
- This fallback becomes the safety net when Ollama times out, a model gives weak output, or no cloud key exists.

Interview explanation:

> I designed Week 3 as a layered local intelligence stack. Clean chunks become searchable evidence, TF-IDF retrieves relevant chunks, and the local Q&A fallback answers only from those sources. This gives users real value without LLM dependency and creates a trustworthy baseline for future Ollama or cloud providers.

Common interviewer question:

> Why not start with embeddings and a vector database?

Strong answer:

> I wanted a deterministic baseline first. TF-IDF is fast, local, testable, and requires no model downloads. Once the app has real documents and evaluation examples, I can compare vector retrieval against TF-IDF instead of adding FAISS or Chroma prematurely.

Common interviewer question:

> How do you prevent hallucination without an LLM?

Strong answer:

> The fallback Q&A does not generate from memory. It retrieves chunks, selects overlapping source sentences, and returns an answer only when evidence exists. If evidence is missing, it says the answer was not found and still shows relevant snippets for user inspection.

## What Was Intentionally Not Built

The current foundation intentionally does not include:

- OCR
- Generated source-grounded answers
- Semantic vector retrieval with FAISS or Chroma
- Local LLM calls
- Cloud AI APIs
- AI-generated summaries
- Authentication
- Payments
- Docker

Interview explanation:

> I avoided fake features. The foundation now has reliable local upload, extraction, and cleaning behavior that can be demonstrated, tested, and extended. AI features will sit on top of this pipeline later.

## Strong Interview Summary

Use this concise explanation:

> I built a local-first AI Research / Thesis Assistant foundation with FastAPI, SQLite, SQLAlchemy, Pydantic schemas, and a service-layer architecture. It supports project CRUD, safe PDF uploads, local PDF extraction, deterministic text cleaning, chunking, document overview, keyword extraction, local statistics analysis, and TF-IDF document search. I intentionally kept AI providers optional so future Q&A can build on clean local document processing instead of depending on paid APIs or model availability.
