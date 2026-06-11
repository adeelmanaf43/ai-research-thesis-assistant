from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_APP = PROJECT_ROOT / "frontend" / "streamlit_app.py"
PAGES_DIR = PROJECT_ROOT / "frontend" / "pages"


def test_hour_three_streamlit_skeleton_exists() -> None:
    assert FRONTEND_APP.exists()
    assert PAGES_DIR.exists()


def test_streamlit_app_shows_required_foundation_content() -> None:
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert "AI Research / Thesis Assistant" in source
    assert "local-first research workspace" in source
    assert "MVP status" in source
    assert "Week 1 foundation is complete" in source
    assert "PDF upload storage" in source
    assert "Backend connection: placeholder only" in source
    assert "does not require paid API keys" in source


def test_pages_folder_is_empty_except_gitkeep() -> None:
    visible_page_files = [path.name for path in PAGES_DIR.iterdir() if path.name != ".gitkeep"]

    assert visible_page_files == []
