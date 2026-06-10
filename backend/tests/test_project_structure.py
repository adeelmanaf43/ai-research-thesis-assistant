from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hour_one_root_structure_exists() -> None:
    required_paths = [
        "backend",
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
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), f"Missing {relative_path}"


def test_env_example_is_local_first_and_secret_free() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///" in env_example
    assert "API_KEY" not in env_example
    assert "SECRET" not in env_example


def test_roadmap_documents_local_first_guardrails() -> None:
    roadmap = (PROJECT_ROOT / "project-roadmap.md").read_text(encoding="utf-8")

    assert "Local processing must work first" in roadmap
    assert "Ollama is optional" in roadmap
    assert "No hardcoded secrets" in roadmap


def test_docs_do_not_hardcode_local_machine_paths() -> None:
    docs_to_check = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "backend" / "README.md",
        PROJECT_ROOT / "docs" / "day1_validation.md",
        PROJECT_ROOT / "docs" / "day3_validation.md",
        PROJECT_ROOT / "docs" / "setup.md",
    ]

    for doc_path in docs_to_check:
        content = doc_path.read_text(encoding="utf-8")
        assert "E:\\portfolio-projects" not in content
        assert "E:/portfolio-projects" not in content


def test_readme_reflects_current_day_four_storage_milestone() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Week 1, Day 4: File storage foundation for documents." in readme
    assert "Project CRUD service layer and FastAPI routes" in readme
    assert "Safe document storage path helpers" in readme
    assert "Document upload API" in readme
    assert "Invoke-WebRequest" in readme
    assert "/api/projects" in readme


def test_api_docs_include_project_endpoint_examples() -> None:
    api_docs = (PROJECT_ROOT / "docs" / "api.md").read_text(encoding="utf-8")

    assert "POST /api/projects" in api_docs
    assert "GET /api/projects" in api_docs
    assert "PATCH /api/projects/{project_id}" in api_docs
    assert "DELETE /api/projects/{project_id}" in api_docs
    assert "422 Unprocessable Entity" in api_docs
    assert "No document upload yet" not in api_docs
