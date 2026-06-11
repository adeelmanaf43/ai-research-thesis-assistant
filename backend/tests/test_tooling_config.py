from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_dev_requirements_include_lint_and_format_tools() -> None:
    requirements = (PROJECT_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "ruff" in requirements
    assert "black" in requirements


def test_pyproject_configures_ruff_and_black() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.ruff]" in pyproject
    assert "line-length = 100" in pyproject
    assert 'target-version = "py311"' in pyproject
    assert "[tool.ruff.lint]" in pyproject
    assert "[tool.black]" in pyproject
    assert 'target-version = ["py311"]' in pyproject


def test_docs_include_quality_commands() -> None:
    docs_to_check = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "backend" / "README.md",
        PROJECT_ROOT / "docs" / "setup.md",
    ]

    for doc_path in docs_to_check:
        content = doc_path.read_text(encoding="utf-8")
        assert "ruff check ." in content
        assert "black --check --workers 1 backend frontend" in content
        assert "black --workers 1 backend frontend" in content
