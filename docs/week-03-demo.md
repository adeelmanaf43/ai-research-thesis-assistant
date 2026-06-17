# Week 3 Demo

This demo shows the local intelligence layer working end to end with `sample_data\thesis.pdf`. It does not require paid API keys, cloud providers, Docker, authentication, Ollama, FAISS, or Chroma.

## What This Demo Proves

- A user can upload a thesis PDF into a local project.
- The backend extracts, cleans, detects sections, chunks, and stores document data locally.
- The app can generate a local overview with keywords and document statistics.
- The app can generate extractive section summaries.
- The app can extract structured research information with rule-based local logic.
- The app can search stored chunks with TF-IDF.
- The app can answer questions from retrieved source chunks without hallucinating.
- The app stores local chat history with `provider_mode="local"`.
- Streamlit can display overview, summaries, search results, and Q&A when the backend is running.

## Prerequisites

Run these commands from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Confirm the local thesis file exists:

```powershell
Test-Path sample_data\thesis.pdf
```

Expected result:

```text
True
```

`thesis.pdf` is intentionally ignored by Git. If it is missing, place a local PDF at `sample_data\thesis.pdf` or adapt the upload command to another private PDF.

## 1. Start Backend

Use port `8020` to avoid older backend processes:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8020 --reload
```

Expected result:

```text
Uvicorn running on http://127.0.0.1:8020
```

Open a second PowerShell window for the remaining commands.

## 2. Check Health

```powershell
Invoke-RestMethod "http://127.0.0.1:8020/health"
```

Expected result:

```text
status : ok
mode   : local-first
```

## 3. Create Project

```powershell
$project = Invoke-RestMethod "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Week 3 Thesis Demo","description":"Local intelligence demo"}'
$project
$projectId = $project.id
```

Expected result:

```text
id          : 1
name        : Week 3 Thesis Demo
description : Local intelligence demo
```

## 4. Upload Thesis PDF

```powershell
$uploadJson = curl.exe -s -X POST "http://127.0.0.1:8020/api/projects/$projectId/documents" -F "file=@sample_data\thesis.pdf;type=application/pdf"
$upload = $uploadJson | ConvertFrom-Json
$upload
$documentId = $upload.id
```

Expected result for the local demo PDF:

```text
status      : processed
page_count  : 78
word_count  : 28682
```

Valid alternatives:

```text
status : ocr_needed
status : extraction_failed
status : chunking_failed
```

Those alternatives mean the upload route worked but the source PDF needs review.

## 5. Fetch Document Overview

```powershell
$overview = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/overview"
$overview
```

Expected result for the local demo PDF:

```text
status       : processed
page_count   : 78
word_count   : 28682
chunk_count  : 53
```

Inspect sections:

```powershell
$overview.detected_sections | Format-Table section_name, detected_heading, confidence
```

Expected result:

```text
At least one detected section appears.
```

## 6. Generate Local Overview Analysis

```powershell
$localOverview = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/analysis/local-overview" -Method Post
$localOverview.analysis_type
$localOverview.output_json.keywords | Select-Object -First 5
```

Expected result:

```text
document_overview_local
```

Expected keyword examples from the local thesis demo:

```text
fatty
food
products
acids
trans
```

## 7. Generate Section Summaries

```powershell
$summaryAnalysis = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/analysis/section-summaries" -Method Post
$summaryAnalysis.analysis_type

$sectionSummaries = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/summaries/sections"
$sectionSummaries.summaries | Select-Object section_name, selected_sentence_count, confidence
```

Expected result:

```text
section_summaries_local
```

Expected local thesis demo result:

```text
About 12 section summaries, depending on extracted headings.
```

## 8. Extract Research Information

```powershell
$researchInfo = Invoke-RestMethod "http://127.0.0.1:8020/api/analysis/$documentId/research-info" -Method Post
$researchInfo.analysis_type
$researchInfo.output_json.fields
```

Expected result:

```text
research_info_local
```

Expected fields:

```text
dataset_sample
findings
future_work
limitations
methodology
objectives
research_problem
research_questions
variables
```

Fields that cannot be found should use honest `null` values and low confidence instead of fabricated content.

## 9. Search Stored Chunks

Use an extracted keyword from the local overview, such as `fatty acids`:

```powershell
$search = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/search?q=fatty%20acids&top_k=3"
$search | Format-Table chunk_index, section_name, score, text_preview
```

Expected result:

```text
3 source chunks with positive TF-IDF scores.
```

If no results appear, try another extracted keyword:

```powershell
Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/search?q=food&top_k=3"
Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/search?q=trans&top_k=3"
```

## 10. Ask Source-Grounded Local Q&A

```powershell
$chat = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/chat" -Method Post -ContentType "application/json" -Body '{"question":"What does the document say about fatty acids?","top_k":3}'
$chat.answer_found
$chat.answer
$chat.source_chunks | Format-Table chunk_index, section_name, score, snippet
```

Expected result:

```text
answer_found : True
source_chunks: 3
```

The answer must be extractive and grounded in returned source snippets. If the answer is not found, the response should say so explicitly.

## 11. Confirm Chat History

Use Python to inspect the local SQLite database:

```powershell
.\.venv\Scripts\python.exe -c "from backend.app.core.database import SessionLocal; from backend.app.models.chat_history import ChatHistory; db=SessionLocal(); print(db.query(ChatHistory).count()); db.close()"
```

Expected result:

```text
At least 1
```

## 12. Open Streamlit Demo

Start Streamlit:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/streamlit_app.py
```

Expected result:

```text
Local URL: http://localhost:8501
```

In the Streamlit page:

1. Enter backend URL `http://127.0.0.1:8020`.
2. Enter `$documentId`.
3. Select `Load Overview`.
4. Enter search query `fatty acids`.
5. Select `Search Document`.
6. Enter question `What does the document say about fatty acids?`.
7. Select `Ask Question`.

Expected UI result:

- Overview metrics appear.
- Processing summary appears.
- Section summaries appear.
- Search results show source chunk previews.
- Q&A answer appears with source snippets.

## Screenshot Placeholders

Add screenshots later under a tracked screenshots folder or paste them into portfolio documentation.

```text
[Screenshot Placeholder 1: Backend health response]
[Screenshot Placeholder 2: Successful thesis.pdf upload response]
[Screenshot Placeholder 3: Document overview metrics]
[Screenshot Placeholder 4: Local overview keywords]
[Screenshot Placeholder 5: Section summaries]
[Screenshot Placeholder 6: Research information extraction]
[Screenshot Placeholder 7: TF-IDF search results]
[Screenshot Placeholder 8: Source-grounded local Q&A]
[Screenshot Placeholder 9: Streamlit overview, search, and Q&A display]
```

## Automated Validation

Run the focused Week 3 checks:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_local_analysis.py backend\tests\test_retrieval.py backend\tests\test_local_provider.py backend\tests\test_chat_service.py backend\tests\test_frontend_structure.py -q
```

Expected result:

```text
All tests pass.
```

Run the full validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
$env:BLACK_CACHE_DIR='data/test_tmp/black_cache_week3_demo'; .\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
```

Expected result at the time this demo was written:

```text
315 passed
All checks passed!
62 files would be left unchanged.
```

## Demo Talking Points

- The app is useful before Ollama because extraction, cleaning, section detection, chunking, keywords, summaries, research info extraction, TF-IDF search, and Q&A fallback all run locally.
- TF-IDF is used before FAISS or Chroma because it is deterministic, lightweight, and easy to validate against SQLite chunks.
- Q&A is source-grounded and extractive; it does not guess when retrieved chunks do not contain an answer.
- Rule-based extraction is honest about unknown fields, which is safer than fake AI confidence.
- Private PDFs and generated demo data are ignored by Git.

## Cleanup

Manual uploads are stored under `data/uploads/`, and temporary test/demo artifacts are stored under `data/test_tmp/`. Both are ignored by Git. Keep them for local testing or remove them when you no longer need them.
