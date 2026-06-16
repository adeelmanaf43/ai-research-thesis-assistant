import pytest
from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models.chat_history import ChatHistory
from backend.app.models.chunk import Chunk
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.chat_service import (
    DocumentChatAnswer,
    answer_document_question,
)
from backend.app.services.document_service import create_document_record, save_uploaded_file
from backend.app.services.project_service import create_project


def _session_factory(workspace_tmp_path):
    database_path = workspace_tmp_path / "chat.db"
    settings = Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=workspace_tmp_path,
        upload_dir=workspace_tmp_path / "uploads",
        export_dir=workspace_tmp_path / "exports",
        database_url=f"sqlite:///{database_path.as_posix()}",
        provider_mode="local",
    )
    database_engine = create_database_engine(settings)
    init_database(database_engine)
    return get_session_factory(database_engine), database_engine, settings


def _create_chat_ready_document(session, settings):
    project = create_project(session, ProjectCreate(name="Chat project"))
    saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
    document = create_document_record(
        session,
        DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
        saved_file.stored_filename,
        saved_file.file_path,
        status="processed",
    )
    session.add_all(
        [
            Chunk(
                document_id=document.id,
                chunk_index=0,
                section_name="Methodology",
                text="The methodology used a survey sample of 120 postgraduate students.",
                word_count=10,
                page_start=2,
                page_end=3,
            ),
            Chunk(
                document_id=document.id,
                chunk_index=1,
                section_name="Conclusion",
                text="The conclusion recommends future report export workflows.",
                word_count=7,
                page_start=8,
                page_end=8,
            ),
        ]
    )
    session.commit()
    return document


def test_answer_document_question_persists_local_chat_history(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_chat_ready_document(session, settings)

        chat_answer = answer_document_question(
            session,
            document.id,
            "What sample did the methodology use?",
            top_k=2,
        )

        assert isinstance(chat_answer, DocumentChatAnswer)
        assert chat_answer.answer_found is True
        assert chat_answer.provider_mode == "local"
        assert "120 postgraduate students" in chat_answer.answer
        source_chunk = chat_answer.source_chunks[0]
        assert source_chunk.chunk_index == 0
        assert source_chunk.section_name == "Methodology"
        assert source_chunk.page_start == 2
        assert source_chunk.page_end == 3
        assert source_chunk.snippet == (
            "The methodology used a survey sample of 120 postgraduate students."
        )
        stored_chat = session.scalar(
            select(ChatHistory).where(ChatHistory.id == chat_answer.chat_id)
        )
        assert stored_chat is not None
        assert stored_chat.project_id == document.project_id
        assert stored_chat.document_id == document.id
        assert stored_chat.question == "What sample did the methodology use?"
        assert stored_chat.answer == chat_answer.answer
        assert stored_chat.provider_mode == "local"

    database_engine.dispose()


def test_answer_document_question_returns_not_found_answer_and_stores_chat(
    workspace_tmp_path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_chat_ready_document(session, settings)

        chat_answer = answer_document_question(
            session,
            document.id,
            "What quantum model was used?",
            top_k=2,
        )

        assert chat_answer.answer_found is False
        assert chat_answer.answer.startswith("I could not find the answer")
        assert chat_answer.source_chunks
        assert chat_answer.source_chunks[0].section_name == "Methodology"
        stored_chat = session.get(ChatHistory, chat_answer.chat_id)
        assert stored_chat is not None
        assert stored_chat.answer == chat_answer.answer

    database_engine.dispose()


def test_answer_document_question_returns_none_for_missing_document(workspace_tmp_path) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        assert answer_document_question(session, 999, "What did the study find?") is None

    database_engine.dispose()


@pytest.mark.parametrize(
    ("document_id", "question", "top_k", "message"),
    [
        (0, "What did the study find?", 5, "Document ID"),
        (1, "   ", 5, "Question"),
        (1, "What did the study find?", 0, "top_k"),
    ],
)
def test_answer_document_question_validates_inputs(
    workspace_tmp_path,
    document_id: int,
    question: str,
    top_k: int,
    message: str,
) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        with pytest.raises(ValueError, match=message):
            answer_document_question(session, document_id, question, top_k=top_k)

    database_engine.dispose()


def test_document_chat_answer_serializes_for_api() -> None:
    chat_answer = DocumentChatAnswer(
        chat_id=1,
        document_id=2,
        question="What sample was used?",
        answer="The sample was 120 students.",
        answer_found=True,
        provider_mode="local",
        source_chunks=[],
        limitations=["Local answer."],
    )

    assert chat_answer.to_dict() == {
        "chat_id": 1,
        "document_id": 2,
        "question": "What sample was used?",
        "answer": "The sample was 120 students.",
        "answer_found": True,
        "provider_mode": "local",
        "source_chunks": [],
        "limitations": ["Local answer."],
    }
