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
