from pathlib import Path

from sqlalchemy import inspect

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models import Analysis, ChatHistory, Chunk, Document, Project, User


EXPECTED_TABLES = {
    "analyses",
    "chat_history",
    "chunks",
    "documents",
    "projects",
    "users",
}


def _settings_for_database(workspace_tmp_path: Path, filename: str) -> Settings:
    return Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{(workspace_tmp_path / filename).as_posix()}",
        provider_mode="local",
    )


def test_model_import_boundary_registers_expected_tables() -> None:
    table_names = {model.__tablename__ for model in (Analysis, ChatHistory, Chunk, Document, Project, User)}

    assert table_names == EXPECTED_TABLES


def test_base_models_create_tables_without_business_workflows(workspace_tmp_path: Path) -> None:
    database_engine = create_database_engine(_settings_for_database(workspace_tmp_path, "models.db"))

    init_database(database_engine)
    table_names = set(inspect(database_engine).get_table_names())

    database_engine.dispose()

    assert table_names == EXPECTED_TABLES


def test_mvp_project_document_graph_can_exist_without_login(workspace_tmp_path: Path) -> None:
    database_engine = create_database_engine(_settings_for_database(workspace_tmp_path, "graph.db"))
    init_database(database_engine)
    session_factory = get_session_factory(database_engine)

    with session_factory() as session:
        project = Project(name="Local thesis project")
        document = Document(
            project=project,
            original_filename="paper.pdf",
            stored_filename="paper.pdf",
            file_path="data/uploads/paper.pdf",
            mime_type="application/pdf",
        )
        chunk = Chunk(document=document, chunk_index=0, text="A source-grounded chunk.", word_count=4)
        analysis = Analysis(
            project=project,
            document=document,
            analysis_type="overview",
            content="Local extractive overview placeholder.",
        )
        chat = ChatHistory(
            project=project,
            document=document,
            question="What is this paper about?",
            answer="A local placeholder answer.",
        )

        session.add_all([project, document, chunk, analysis, chat])
        session.commit()

        assert project.id is not None
        assert project.user_id is None
        assert document.id is not None
        assert chunk.id is not None
        assert analysis.provider_mode == "local"
        assert chat.provider_mode == "local"

    database_engine.dispose()
