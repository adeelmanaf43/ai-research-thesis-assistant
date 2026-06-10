from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hour_two_backend_skeleton_exists() -> None:
    required_paths = [
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/core/database.py",
        "backend/app/api/__init__.py",
        "backend/tests/__init__.py",
        "backend/requirements.txt",
        "backend/README.md",
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), f"Missing {relative_path}"


def test_backend_requirements_are_local_first() -> None:
    requirements = (PROJECT_ROOT / "backend/requirements.txt").read_text(encoding="utf-8")

    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "python-dotenv" in requirements
    assert "openai" not in requirements.lower()
    assert "anthropic" not in requirements.lower()


def test_backend_readme_documents_hour_four_commands() -> None:
    readme = (PROJECT_ROOT / "backend/README.md").read_text(encoding="utf-8")

    assert "python -m venv .venv" in readme
    assert "pip install -r backend/requirements.txt" in readme
    assert "pip install -r requirements-dev.txt" in readme
    assert "python -m uvicorn backend.app.main:app --reload" in readme
    assert "python -m pytest backend/tests/test_health_api.py" in readme
    assert "http://127.0.0.1:8000/health" in readme


def test_backend_readme_documents_database_base() -> None:
    readme = (PROJECT_ROOT / "backend/README.md").read_text(encoding="utf-8")

    assert "SQLAlchemy with SQLite" in readme
    assert "DATABASE_URL" in readme
    assert "init_database()" in readme
    assert "users" in readme
    assert "projects" in readme
    assert "documents" in readme
    assert "`Project.user_id` is nullable" in readme


def test_backend_readme_documents_project_api_examples() -> None:
    readme = (PROJECT_ROOT / "backend/README.md").read_text(encoding="utf-8")

    assert "Project API Examples" in readme
    assert 'Method Post' in readme
    assert "/api/projects" in readme
    assert "201 Created" in readme
    assert "204 No Content" in readme


def test_backend_readme_documents_document_storage_foundation() -> None:
    readme = (PROJECT_ROOT / "backend/README.md").read_text(encoding="utf-8")

    assert "Document Storage Foundation" in readme
    assert "uploads/" in readme
    assert "projects/" in readme
    assert "{project_id}/" in readme
    assert "documents/" in readme
    assert "document_storage.py" in readme
    assert "sanitize_upload_filename()" in readme


def test_pytest_config_points_to_backend_tests() -> None:
    pytest_config = (PROJECT_ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert "testpaths = backend/tests" in pytest_config
    assert "pythonpath = ." in pytest_config
