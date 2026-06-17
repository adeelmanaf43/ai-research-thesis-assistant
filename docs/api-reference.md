# API Reference

This reference documents the current API surface for the local-first AI Research / Thesis Assistant through Week 3 Day 4. The API works without paid API keys, cloud providers, Docker, authentication, or mandatory Ollama.

Base URL for local development:

```text
http://127.0.0.1:8000
```

## Current Endpoints

| Method   | Path                                                  | Purpose                                      |
| -------- | ----------------------------------------------------- | -------------------------------------------- |
| `GET`    | `/`                                                   | Basic app readiness metadata                 |
| `GET`    | `/health`                                             | Local health check                           |
| `GET`    | `/api/v1/health`                                      | Versioned health check                       |
| `POST`   | `/api/projects`                                       | Create a local research project              |
| `GET`    | `/api/projects`                                       | List local research projects                 |
| `GET`    | `/api/projects/{project_id}`                          | Fetch one project by ID                      |
| `PATCH`  | `/api/projects/{project_id}`                          | Update project name or description           |
| `DELETE` | `/api/projects/{project_id}`                          | Delete a project                             |
| `GET`    | `/api/projects/{project_id}/documents`                | List documents in one project                |
| `POST`   | `/api/projects/{project_id}/documents`                | Upload one PDF into an existing project      |
| `GET`    | `/api/documents/{document_id}/overview`               | Fetch local document processing overview     |
| `POST`   | `/api/documents/{document_id}/analysis/local-overview` | Generate and store local overview analysis   |
| `GET`    | `/api/documents/{document_id}/analysis/local-overview` | Fetch latest stored local overview analysis  |
| `GET`    | `/api/documents/{document_id}/summaries/sections`     | Fetch local extractive summaries by section  |
| `GET`    | `/api/documents/{document_id}/search`                 | Search stored chunks locally with TF-IDF     |
| `POST`   | `/api/documents/{document_id}/chat`                   | Ask a local source-grounded document question |
| `POST`   | `/api/documents/{document_id}/analysis/section-summaries` | Generate and store local section summaries |
| `POST`   | `/api/analysis/{document_id}/research-info`           | Generate and store local research info extraction |

## Health

### `GET /`

Returns basic application readiness metadata.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/"
```

Example response:

```json
{
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "status": "ready",
  "mode": "local-first"
}
```

### `GET /health`

Returns the local health status.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
```

Example response:

```json
{
  "status": "ok",
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "environment": "local",
  "mode": "local-first"
}
```

### `GET /api/v1/health`

Returns the same health payload through a versioned path for future integrations.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/v1/health"
```

Expected status: `200 OK`

## Projects

Project endpoints manage local research workspaces. Authentication is intentionally not required in the current local-first foundation.

### `POST /api/projects`

Creates a project.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Request body:

```json
{
  "name": "Thesis project",
  "description": "Local workspace"
}
```

Example response:

```json
{
  "id": 1,
  "user_id": null,
  "name": "Thesis project",
  "description": "Local workspace",
  "created_at": "2026-06-11T10:00:00",
  "updated_at": "2026-06-11T10:00:00"
}
```

Expected status: `201 Created`

Validation:

- `name` is required.
- Leading and trailing whitespace in `name` is stripped.
- Empty or whitespace-only names return `422 Unprocessable Entity`.

### `GET /api/projects`

Lists projects, newest first.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Example response:

```json
[
  {
    "id": 1,
    "user_id": null,
    "name": "Thesis project",
    "description": "Local workspace",
    "created_at": "2026-06-11T10:00:00",
    "updated_at": "2026-06-11T10:00:00"
  }
]
```

Expected status: `200 OK`

### `GET /api/projects/{project_id}`

Returns one project by ID.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1"
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.

Example not found response:

```json
{
  "detail": "Project not found."
}
```

### `PATCH /api/projects/{project_id}`

Updates a project name or description.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Patch -ContentType "application/json" -Body '{"name":"Updated thesis project"}'
```

Request body:

```json
{
  "name": "Updated thesis project"
}
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.
- `422 Unprocessable Entity` when `name` is empty or whitespace only.

### `DELETE /api/projects/{project_id}`

Deletes one project.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Delete
```

Expected status:

- `204 No Content` when the project is deleted.
- `404 Not Found` when the project does not exist.

## Documents

Document endpoints currently support PDF upload, metadata storage, local PyMuPDF extraction, deterministic text cleaning, internal rule-based section detection, and internal chunk persistence. They do not summarize, search, or run AI analysis yet.

### `GET /api/projects/{project_id}/documents`

Lists documents for one existing project, newest first.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1/documents"
```

Example response:

```json
[
  {
    "id": 1,
    "project_id": 1,
    "original_filename": "invoice_GAF-175351693.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 1024,
    "page_count": 1,
    "word_count": 120,
    "status": "processed",
    "extraction_error": null,
    "uploaded_at": "2026-06-11T10:00:00"
  }
]
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.

Response boundary:

- Internal storage fields are not exposed.
- Cleaned text paths, extracted text paths, and raw chunk records are not exposed.

### `POST /api/projects/{project_id}/documents`

Uploads one PDF file into an existing project.

Example request:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

Request type: `multipart/form-data`

Required field:

- `file`: a PDF file

Example response:

```json
{
  "id": 1,
  "project_id": 1,
  "original_filename": "invoice_GAF-175351693.pdf",
  "mime_type": "application/pdf",
  "file_size_bytes": 1024,
  "page_count": 1,
  "word_count": 120,
  "status": "processed",
  "extraction_error": null,
  "uploaded_at": "2026-06-11T10:00:00"
}
```

Expected status:

- `201 Created` when the PDF is saved and the metadata record is created.
- `404 Not Found` when the project does not exist.
- `400 Bad Request` when the filename extension is not `.pdf`.
- `400 Bad Request` when a provided content type is not `application/pdf` or `application/x-pdf`.
- `413 Content Too Large` when the file exceeds `MAX_UPLOAD_FILE_SIZE_BYTES`.
- `422 Unprocessable Entity` when the multipart `file` field is missing.
- `500 Internal Server Error` when local storage fails.

Extraction behavior:

- Valid PDFs are parsed locally with PyMuPDF after saving.
- Successful extraction runs deterministic text cleaning, saves internal `.extracted.txt` and `.cleaned.txt` artifacts, populates `page_count`, and populates `word_count`.
- Section detection runs on cleaned text and stores structured sections in an internal `section_detection` analysis record.
- Chunking runs after section detection and stores internal chunks. Normal successful documents use `status` value `processed` only after chunks are stored.
- PDFs that save successfully but cannot be parsed still return `201 Created`.
- Extraction failures set `status` to `extraction_failed` and return `extraction_error`.
- PDFs with very little extractable text use `status` value `ocr_needed` and return an OCR warning in `extraction_error`.

Processed document lifecycle:

```text
upload PDF
  -> save original file locally
  -> create document metadata row
  -> extract text with PyMuPDF
  -> clean extracted text
  -> save internal extracted/cleaned text artifacts
  -> detect academic sections
  -> store internal section_detection analysis
  -> create overlapping chunks with section metadata
  -> replace stored chunks transactionally
  -> mark document status as processed
```

Failure status meanings:

| Status                     | Meaning                                                              |
| -------------------------- | -------------------------------------------------------------------- |
| `processed`                | Text was extracted, cleaned, sectioned, chunked, and chunks stored   |
| `ocr_needed`               | Upload saved, but very little text was extractable                   |
| `extraction_failed`        | Upload saved, but local PDF parsing failed                           |
| `text_processing_failed`   | Upload and extraction worked, but text artifact storage failed       |
| `section_detection_failed` | Cleaning worked, but section analysis storage failed                 |
| `chunking_failed`          | Section detection worked, but chunk storage failed                   |

### `GET /api/documents/{document_id}/overview`

Returns a local processing overview for one document.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/overview"
```

Example response:

```json
{
  "document_id": 1,
  "filename": "invoice_GAF-175351693.pdf",
  "status": "processed",
  "page_count": 1,
  "word_count": 120,
  "chunk_count": 3,
  "detected_sections": [
    {
      "section_name": "Title",
      "detected_heading": "Title",
      "confidence": 0.75
    }
  ],
  "extraction_warnings": [],
  "processing_summary": {
    "status": "processed",
    "message": "Document processed locally with 1 detected sections and 3 stored chunks.",
    "is_complete": true,
    "requires_attention": false,
    "next_step": "Review the overview or continue with the next local analysis step."
  }
}
```

Expected status:

- `200 OK` when the document exists.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Overview behavior:

- `chunk_count` is counted from stored local chunk rows.
- `detected_sections` is read from the latest stored `section_detection` analysis.
- `extraction_warnings` combines extraction errors and cleaning warnings.
- `processing_summary` is structured for frontend use and includes status, message, completion state, attention state, and next-step guidance.
- No AI provider, Ollama model, or cloud API is called.

User-friendly errors:

- Missing documents return `Document not found. Upload a document or use an existing document ID.`
- Invalid document IDs return `Document ID must be a positive integer.`

Response boundary:

- `file_path` is intentionally not exposed.
- `stored_filename` is intentionally not exposed.
- `extracted_text_path` and `cleaned_text_path` are intentionally not exposed.
- Chunk records are intentionally not exposed through this upload response.
- The original filename is returned for user clarity.
- Saved files remain under the configured local upload directory.

### `POST /api/documents/{document_id}/analysis/local-overview`

Generates deterministic local overview analysis for a processed document and stores it in the `analyses` table as `analysis_type="document_overview_local"`.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/local-overview" -Method Post
```

Example response:

```json
{
  "id": 3,
  "document_id": 1,
  "analysis_type": "document_overview_local",
  "title": "Local document overview analysis",
  "provider_mode": "local",
  "output_json": {
    "document_id": 1,
    "filename": "invoice_GAF-175351693.pdf",
    "keywords": [
      {
        "keyword": "retrieval",
        "score": 0.699537,
        "frequency": 3
      }
    ],
    "statistics": {
      "total_word_count": 120,
      "word_count_by_section": {
        "Introduction": 40
      },
      "chunk_count_by_section": {
        "Introduction": 1
      },
      "reference_count_estimate": 2,
      "readability": {
        "sentence_count": 8,
        "average_words_per_sentence": 15.0,
        "average_syllables_per_word": 1.7,
        "flesch_reading_ease": 47.76
      }
    }
  },
  "created_at": "2026-06-14T10:00:00"
}
```

Expected status:

- `201 Created` when analysis is generated and stored.
- `404 Not Found` when the document does not exist.
- `409 Conflict` when cleaned text is not available yet.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

### `GET /api/documents/{document_id}/analysis/local-overview`

Fetches the latest stored local overview analysis for one document. This endpoint does not regenerate analysis.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/local-overview"
```

Expected status:

- `200 OK` when stored local overview analysis exists.
- `404 Not Found` when no stored local overview analysis exists.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Local overview analysis behavior:

- Uses cleaned text from the local processing pipeline.
- Extracts top keywords locally with stopword filtering and deterministic scoring.
- Computes word counts by section, chunk counts by section, reference count estimate, and basic readability metrics.
- Stores output JSON in SQLite under `analysis_type="document_overview_local"`.
- Does not call Ollama, cloud providers, or paid APIs.

### `GET /api/documents/{document_id}/summaries/sections`

Returns concise extractive summaries for supported detected sections. Summaries are built from stored `section_detection` output and select original source sentences instead of generating new prose.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/summaries/sections"
```

Example response:

```json
{
  "document_id": 1,
  "summaries": [
    {
      "section_name": "Results",
      "section_type": "results",
      "summary": "Retrieval accuracy improved when clean chunks preserved evidence.",
      "selected_sentence_count": 1,
      "source_sentence_indexes": [1],
      "confidence": 0.8,
      "limitations": [
        "Extractive summary uses original sentences only and does not rewrite or infer missing context."
      ]
    }
  ],
  "source_section_names": ["Results"],
  "limitations": [
    "Summaries are extractive and local; they select source sentences instead of generating new prose."
  ]
}
```

Expected status:

- `200 OK` when the document exists.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Section summary behavior:

- Supports abstract, introduction, methodology, results, discussion, and conclusion.
- Supports literature review summaries when that section is detected.
- Skips unsupported sections such as title and references.
- Skips empty sections, table-of-contents fragments, obvious figure/table captions, URLs, and reference-like fragments.
- Returns the best non-empty summary per section type when duplicate headings are detected.
- Returns source section names and source sentence indexes for traceability.
- Includes confidence and limitations because section detection and sentence scoring are heuristic.
- Does not call Ollama, cloud providers, or paid APIs.

### `GET /api/documents/{document_id}/search`

Searches stored chunks for one document with local TF-IDF retrieval.

Query parameters:

- `q`: required search query.
- `top_k`: optional maximum number of chunks to return. Default is `5`, maximum is `10`.
- `include_full_text`: optional boolean. Default is `false`.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/search?q=methodology%20sample&top_k=3"
```

Example response:

```json
[
  {
    "chunk_id": 12,
    "chunk_index": 3,
    "section_name": "Methodology",
    "page_start": 4,
    "page_end": 5,
    "score": 0.73421,
    "text_preview": "The methodology used a survey sample of postgraduate thesis writers.",
    "full_text": null
  }
]
```

Expected status:

- `200 OK` when the document exists. Returns an empty list when no chunks match.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID, query, or `top_k` is invalid.
- `503 Service Unavailable` when local TF-IDF dependencies are not installed.

Search behavior:

- Uses stored chunk text only.
- Returns preview-first results by default.
- Can include full chunk text with `include_full_text=true`.
- Does not generate answers, call Ollama, call cloud providers, or perform semantic retrieval.

### `POST /api/documents/{document_id}/chat`

Retrieves top chunks for a document, creates a local extractive answer, stores chat history, and returns the answer with source chunks.

Request body:

- `question`: required user question.
- `top_k`: optional maximum number of retrieved chunks to use. Default is `5`, maximum is `10`.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/chat" -Method Post -ContentType "application/json" -Body '{"question":"What sample did the methodology use?","top_k":3}'
```

Example response:

```json
{
  "chat_id": 8,
  "document_id": 1,
  "question": "What sample did the methodology use?",
  "answer": "The methodology used a survey sample of postgraduate thesis writers.",
  "answer_found": true,
  "provider_mode": "local",
  "source_chunks": [
    {
      "chunk_id": 12,
      "chunk_index": 3,
      "section_name": "Methodology",
      "page_start": 4,
      "page_end": 5,
      "score": 0.73421,
      "snippet": "The methodology used a survey sample of postgraduate thesis writers."
    }
  ],
  "limitations": [
    "Local fallback answers are extractive and use only retrieved source chunks.",
    "If retrieved chunks do not contain the answer, the provider must say so."
  ]
}
```

Expected status:

- `201 Created` when the document exists and chat history is stored.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID, question, or `top_k` is invalid.
- `503 Service Unavailable` when local TF-IDF dependencies are not installed.

Chat behavior:

- Retrieves chunks with local TF-IDF search.
- Answers extractively from retrieved chunks only.
- Stores `question`, `answer`, `document_id`, `project_id`, and `provider_mode="local"` in `chat_history`.
- Says when the answer is not found instead of guessing.
- Does not call Ollama, cloud providers, or paid APIs.

### `POST /api/documents/{document_id}/analysis/section-summaries`

Generates local extractive section summaries and stores the output JSON in SQLite under `analysis_type="section_summaries_local"` with `provider_mode="local"`.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/analysis/section-summaries" -Method Post
```

Example response:

```json
{
  "id": 4,
  "document_id": 1,
  "analysis_type": "section_summaries_local",
  "title": "Local section summaries",
  "provider_mode": "local",
  "output_json": {
    "document_id": 1,
    "summaries": [
      {
        "section_name": "Results",
        "section_type": "results",
        "summary": "Retrieval accuracy improved when clean chunks preserved evidence.",
        "selected_sentence_count": 1,
        "source_sentence_indexes": [1],
        "confidence": 0.8,
        "limitations": [
          "Extractive summary uses original sentences only and does not rewrite or infer missing context."
        ]
      }
    ],
    "source_section_names": ["Results"],
    "limitations": [
      "Summaries are extractive and local; they select source sentences instead of generating new prose."
    ]
  },
  "created_at": "2026-06-14T10:00:00"
}
```

Expected status:

- `201 Created` when summaries are generated and stored.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Persistence behavior:

- Saves the same source-grounded summary payload returned by the section summary endpoint.
- Stores `provider_mode="local"` because no LLM provider is called.
- Can store an empty summaries list with limitations when a document exists but has no stored section detection output.

### `POST /api/analysis/{document_id}/research-info`

Generates local rule-based research information extraction and stores the output JSON in SQLite under `analysis_type="research_info_local"` with `provider_mode="local"`.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/analysis/1/research-info" -Method Post
```

Example response:

```json
{
  "id": 5,
  "document_id": 1,
  "analysis_type": "research_info_local",
  "title": "Local research information extraction",
  "provider_mode": "local",
  "output_json": {
    "document_id": 1,
    "filename": "paper.pdf",
    "fields": {
      "research_problem": {
        "field": "research_problem",
        "extracted_text": "The problem is that thesis writers lack source-grounded review tools.",
        "source_section": "Introduction",
        "confidence": 0.7
      },
      "findings": {
        "field": "findings",
        "extracted_text": null,
        "source_section": null,
        "confidence": 0.0
      }
    },
    "warnings": []
  },
  "created_at": "2026-06-14T10:00:00"
}
```

Expected status:

- `201 Created` when research information is generated and stored.
- `404 Not Found` when the document does not exist.
- `409 Conflict` when cleaned text is not available yet.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Research information behavior:

- Extracts research problem, objectives, research questions, methodology, dataset/sample, variables, findings, limitations, and future work using local rules.
- Returns honest `null` text/source and `0.0` confidence for fields that are not found.
- Uses cleaned text and stored section detection output when available.
- Does not call Ollama, cloud providers, or paid APIs.
- Works best when the PDF contains clear academic phrasing such as "objective", "research question", "methodology", "sample", "findings", "limitation", or "future work".
- Does not perform semantic inference. Implied goals, unusual section wording, damaged PDF text, or OCR-only documents may produce missing fields or lower-confidence results.

## Known Limitations

- No OCR processing for scanned PDFs yet.
- Text cleaning artifacts are stored internally but are not exposed through API responses yet.
- Section detection output is exposed only as safe overview metadata, not as raw full section text.
- Section detection is rule-based and depends on extracted heading text. It can miss non-standard academic structures, merge unsupported sections into the nearest known section, or infer a weak title from the first non-empty line.
- Section confidence values are explainable heuristic scores, not statistical model confidence.
- Chunks are stored internally; only aggregate `chunk_count` is exposed through the overview response.
- Local keyword/statistics analysis, persisted extractive section summaries, persisted research information extraction, local TF-IDF document search, and local extractive chat exist, but no generative RAG, comparison, or export yet.
- No auth or permissions layer yet.
- No Ollama or cloud provider calls yet.
- Upload validation checks extension, provided content type, and configured file size before local extraction.

These limitations are intentional for the current milestone. The API establishes a stable local-first processing and analysis foundation before search, Q&A, provider integrations, and export workflows are added.

## Manual Smoke Test

If port `8000` is already used by an old backend process, run the backend on port `8020` and verify the project and upload flow:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

```powershell
curl.exe -X POST "http://127.0.0.1:8020/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

The upload response should include `page_count`, `word_count`, `status`, and `extraction_error`.

List uploaded project documents:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects/1/documents"
```

Fetch the document overview:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/documents/1/overview"
```
