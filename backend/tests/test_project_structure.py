from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hour_one_root_structure_exists() -> None:
    required_paths = [
        "backend",
        "backend/app/services/document_extraction.py",
        "backend/app/services/text_cleaning.py",
        "frontend",
        "docs",
        "sample_data",
        ".gitignore",
        ".env.example",
        "README.md",
        "project-roadmap.md",
        "docs/day1_validation.md",
        "docs/day2_validation.md",
        "docs/day3_validation.md",
        "docs/day4_validation.md",
        "docs/day5_validation.md",
        "docs/week2-day1-validation.md",
        "docs/api-reference.md",
        "docs/weekly-progress.md",
        "docs/learning-notes.md",
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), f"Missing {relative_path}"


def test_env_example_is_local_first_and_secret_free() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///" in env_example
    assert "MAX_UPLOAD_FILE_SIZE_BYTES=" in env_example
    assert "API_KEY" not in env_example
    assert "SECRET" not in env_example


def test_gitignore_excludes_generated_upload_contents() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "data/*" in gitignore
    assert "!data/uploads/" in gitignore
    assert "data/uploads/*" in gitignore
    assert "!data/uploads/.gitkeep" in gitignore


def test_roadmap_documents_local_first_guardrails() -> None:
    roadmap = (PROJECT_ROOT / "project-roadmap.md").read_text(encoding="utf-8")

    assert "Local processing must work first" in roadmap
    assert "Ollama is optional" in roadmap
    assert "No hardcoded secrets" in roadmap


def test_docs_do_not_hardcode_local_machine_paths() -> None:
    docs_to_check = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "backend" / "README.md",
        PROJECT_ROOT / "docs" / "api-reference.md",
        PROJECT_ROOT / "docs" / "weekly-progress.md",
        PROJECT_ROOT / "docs" / "learning-notes.md",
        PROJECT_ROOT / "docs" / "day1_validation.md",
        PROJECT_ROOT / "docs" / "day3_validation.md",
        PROJECT_ROOT / "docs" / "day4_validation.md",
        PROJECT_ROOT / "docs" / "day5_validation.md",
        PROJECT_ROOT / "docs" / "week2-day1-validation.md",
        PROJECT_ROOT / "docs" / "setup.md",
    ]

    for doc_path in docs_to_check:
        content = doc_path.read_text(encoding="utf-8")
        assert "E:\\portfolio-projects" not in content
        assert "E:/portfolio-projects" not in content


def test_readme_reflects_current_text_cleaning_milestone() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Week 2, Day 2: Text cleaning service." in readme
    assert "Project CRUD service layer and FastAPI routes" in readme
    assert "Safe document storage path helpers" in readme
    assert "Document service placeholders" in readme
    assert "PDF-only document upload API" in readme
    assert "Local PDF text extraction service using PyMuPDF" in readme
    assert "ocr_needed" in readme
    assert "Deterministic text cleaning pipeline" in readme
    assert "Internal extracted-text and cleaned-text artifacts" in readme
    assert "Ruff linting and Black formatting configuration" in readme
    assert "docs/api-reference.md" in readme
    assert "docs/weekly-progress.md" in readme
    assert "docs/week2-day1-validation.md" in readme
    assert "docs/learning-notes.md" in readme
    assert "docs/day4_validation.md" in readme
    assert "docs/day5_validation.md" in readme
    assert "Invoke-WebRequest" in readme
    assert "/api/projects" in readme


def test_readme_has_portfolio_sections() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    required_sections = [
        "## Problem",
        "## Solution",
        "## Architecture",
        "## Tech Stack",
        "## Setup",
        "## Current Features",
        "## Roadmap",
        "## Limitations",
        "## Screenshots",
    ]

    for section in required_sections:
        assert section in readme


def test_api_docs_include_project_endpoint_examples() -> None:
    api_docs = (PROJECT_ROOT / "docs" / "api.md").read_text(encoding="utf-8")

    assert "POST /api/projects" in api_docs
    assert "GET /api/projects" in api_docs
    assert "PATCH /api/projects/{project_id}" in api_docs
    assert "DELETE /api/projects/{project_id}" in api_docs
    assert "POST /api/projects/{project_id}/documents" in api_docs
    assert "422 Unprocessable Entity" in api_docs
    assert "No document upload yet" not in api_docs


def test_api_reference_documents_current_endpoints_and_boundaries() -> None:
    api_reference = (PROJECT_ROOT / "docs" / "api-reference.md").read_text(encoding="utf-8")

    required_content = [
        "API Reference",
        "Current Endpoints",
        "GET /",
        "GET /health",
        "GET /api/v1/health",
        "POST /api/projects",
        "GET /api/projects",
        "GET /api/projects/{project_id}",
        "PATCH /api/projects/{project_id}",
        "DELETE /api/projects/{project_id}",
        "POST /api/projects/{project_id}/documents",
        "Example request",
        "Example response",
        "Known Limitations",
        "sample_data\\invoice_GAF-175351693.pdf",
        "file_path",
        "stored_filename",
        "extracted_text_path",
        "cleaned_text_path",
        "No Ollama or cloud provider calls yet",
    ]

    for expected_text in required_content:
        assert expected_text in api_reference

    assert "sample_data\\example.pdf" not in api_reference
    assert "paid API keys" in api_reference


def test_weekly_progress_summarizes_week_one_and_next_steps() -> None:
    weekly_progress = (PROJECT_ROOT / "docs" / "weekly-progress.md").read_text(encoding="utf-8")

    required_content = [
        "Week 1 Summary",
        "Completed Features",
        "Demo Steps",
        "Next Week Plan",
        "Known Week 1 Limitations",
        "Interview Summary",
        "Project CRUD",
        "PDF-only document upload",
        "sample_data\\invoice_GAF-175351693.pdf",
        "local PDF text extraction",
        "No PDF extraction",
        "paid API keys",
        "mandatory Ollama",
    ]

    for expected_text in required_content:
        assert expected_text in weekly_progress

    assert "sample_data\\example.pdf" not in weekly_progress
    assert "Week 2 Day 1 Update" in weekly_progress
    assert "ocr_needed" in weekly_progress


def test_day_four_validation_documents_upload_security() -> None:
    validation_doc = (PROJECT_ROOT / "docs" / "day4_validation.md").read_text(encoding="utf-8")

    assert "Week 1 Day 4 Validation" in validation_doc
    assert "POST /api/projects/{project_id}/documents" in validation_doc
    assert "Filename sanitization" in validation_doc
    assert "Path traversal" in validation_doc
    assert "Generated files under `data/uploads/` are ignored by Git" in validation_doc


def test_learning_notes_cover_week_one_interview_topics() -> None:
    learning_notes = (PROJECT_ROOT / "docs" / "learning-notes.md").read_text(encoding="utf-8")

    assert "Week 1 Learning Notes" in learning_notes
    assert "local-first" in learning_notes
    assert "service layer" in learning_notes
    assert "PDF Upload API" in learning_notes
    assert "Testing Strategy" in learning_notes
    assert "Quality Baseline" in learning_notes
    assert "Strong Interview Summary" in learning_notes


def test_learning_notes_explain_week_two_cleaning_before_chunking_and_ai() -> None:
    learning_notes = (PROJECT_ROOT / "docs" / "learning-notes.md").read_text(encoding="utf-8")

    assert "Week 2 Document Processing" in learning_notes
    assert "Why Cleaning Comes Before Chunking" in learning_notes
    assert "Why Cleaning Comes Before AI" in learning_notes
    assert "Text Cleaning Testing Strategy" in learning_notes
    assert "quality gate before chunking" in learning_notes
    assert "AI as a cleanup shortcut" in learning_notes
    assert ".cleaned.txt" in learning_notes


def test_day_five_validation_documents_quality_baseline() -> None:
    validation_doc = (PROJECT_ROOT / "docs" / "day5_validation.md").read_text(encoding="utf-8")

    assert "Week 1 Day 5 Validation" in validation_doc
    assert "Ruff" in validation_doc
    assert "Black" in validation_doc
    assert "pytest" in validation_doc
    assert "portfolio-ready project overview" in validation_doc


def test_document_upload_examples_reference_existing_sample_file() -> None:
    sample_file = PROJECT_ROOT / "sample_data" / "invoice_GAF-175351693.pdf"
    docs_to_check = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "backend" / "README.md",
        PROJECT_ROOT / "docs" / "api.md",
        PROJECT_ROOT / "docs" / "day4_validation.md",
        PROJECT_ROOT / "docs" / "usage.md",
    ]

    assert sample_file.exists()
    for doc_path in docs_to_check:
        content = doc_path.read_text(encoding="utf-8")
        assert "sample_data\\invoice_GAF-175351693.pdf" in content
        assert "sample_data\\example.pdf" not in content


def test_week_one_followup_docs_reflect_completed_foundation() -> None:
    limitations = (PROJECT_ROOT / "docs" / "known_limitations.md").read_text(encoding="utf-8")
    next_steps = (PROJECT_ROOT / "docs" / "next_steps.md").read_text(encoding="utf-8")

    assert "Week 2 foundation" in limitations
    assert "Week 2 sequence" in next_steps
    assert "Store extracted and cleaned full text" in next_steps


def test_pdf_extraction_dependency_and_docs_are_present() -> None:
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    backend_requirements = (PROJECT_ROOT / "backend" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "PyMuPDF" in requirements
    assert "PyMuPDF" in backend_requirements
    assert "document_extraction.py" in architecture
    assert "per-page text list" in architecture
    assert "ocr_needed" in architecture
    assert "attempts local PyMuPDF extraction" in (PROJECT_ROOT / "README.md").read_text(
        encoding="utf-8"
    )


def test_text_cleaning_service_and_docs_are_present() -> None:
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    roadmap = (PROJECT_ROOT / "project-roadmap.md").read_text(encoding="utf-8")

    assert "text_cleaning.py" in architecture
    assert "run_text_cleaning_pipeline()" in architecture
    assert "Deterministic text cleaning pipeline" in readme
    assert "cleaning statistics" in readme
    assert ".cleaned.txt" in architecture
    assert "PDF Extraction, Cleaning, and Processing Pipeline" in roadmap
    assert "Week 2 Day 2 Update" in (PROJECT_ROOT / "docs" / "weekly-progress.md").read_text(
        encoding="utf-8"
    )


def test_week_two_day_one_validation_documents_processing_behavior() -> None:
    validation_doc = (PROJECT_ROOT / "docs" / "week2-day1-validation.md").read_text(
        encoding="utf-8"
    )

    assert "Week 2 Day 1 Validation" in validation_doc
    assert "document_extraction.py" in validation_doc
    assert "extraction_failed" in validation_doc
    assert "ocr_needed" in validation_doc
    assert "PyMuPDF" in validation_doc
