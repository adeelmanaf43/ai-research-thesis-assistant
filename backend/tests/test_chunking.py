import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models.chunk import Chunk
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.chunking import (
    DEFAULT_CHUNK_SIZE_WORDS,
    DEFAULT_OVERLAP_WORDS,
    MAX_CHUNK_SIZE_WORDS,
    MAX_OVERLAP_WORDS,
    MAX_SINGLE_CHUNK_WORDS,
    MIN_CHUNK_SIZE_WORDS,
    MIN_OVERLAP_WORDS,
    ChunkPersistenceError,
    TextChunk,
    replace_document_chunks,
    split_sections_into_chunks,
    split_text_into_chunks,
)
from backend.app.services.document_service import create_document_record, save_uploaded_file
from backend.app.services.project_service import create_project
from backend.app.services.section_detection import detect_sections


def _session_factory(workspace_tmp_path):
    database_path = workspace_tmp_path / "chunking.db"
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


def _create_document(session, settings):
    project = create_project(session, ProjectCreate(name="Chunk project"))
    saved_file = save_uploaded_file(settings.upload_dir, project.id, "paper.pdf", b"content")
    return create_document_record(
        session,
        DocumentCreate(project_id=project.id, original_filename="paper.pdf"),
        saved_file.stored_filename,
        saved_file.file_path,
    )


def _make_words(count: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{index}" for index in range(count))


def test_split_text_into_chunks_returns_empty_list_for_blank_text() -> None:
    assert split_text_into_chunks("   ") == []
    assert split_text_into_chunks(None) == []


def test_split_text_into_chunks_keeps_short_text_as_single_chunk() -> None:
    chunks = split_text_into_chunks(
        "A short cleaned paragraph for local processing.",
        section_name="Abstract",
        page_count=3,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].section_name == "Abstract"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 3
    assert chunks[0].word_count == 7
    assert chunks[0].text == "A short cleaned paragraph for local processing."


def test_split_text_into_chunks_keeps_near_boundary_text_as_single_chunk() -> None:
    chunks = split_text_into_chunks(_make_words(MAX_SINGLE_CHUNK_WORDS))

    assert len(chunks) == 1
    assert chunks[0].word_count == MAX_SINGLE_CHUNK_WORDS


def test_split_text_into_chunks_splits_when_valid_overlap_is_possible() -> None:
    chunks = split_text_into_chunks(
        _make_words(850),
        chunk_size_words=500,
        overlap_words=150,
    )

    assert [chunk.word_count for chunk in chunks] == [500, 500]
    assert chunks[0].text.split()[-150:] == chunks[1].text.split()[:150]


def test_split_text_into_chunks_uses_default_section_name_when_blank() -> None:
    chunks = split_text_into_chunks(
        "Short local text.",
        section_name="   ",
    )

    assert len(chunks) == 1
    assert chunks[0].section_name == "Unknown"


def test_split_text_into_chunks_uses_default_size_and_overlap() -> None:
    text = _make_words(1_275)

    chunks = split_text_into_chunks(text, section_name="Methodology")

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].word_count == DEFAULT_CHUNK_SIZE_WORDS
    assert chunks[1].word_count == DEFAULT_CHUNK_SIZE_WORDS
    assert (
        chunks[0].text.split()[-DEFAULT_OVERLAP_WORDS:]
        == chunks[1].text.split()[:DEFAULT_OVERLAP_WORDS]
    )
    assert chunks[0].section_name == "Methodology"
    assert chunks[1].section_name == "Methodology"


def test_split_text_into_chunks_accepts_minimum_size_and_overlap() -> None:
    chunks = split_text_into_chunks(
        _make_words(900),
        chunk_size_words=MIN_CHUNK_SIZE_WORDS,
        overlap_words=MIN_OVERLAP_WORDS,
    )

    assert [chunk.word_count for chunk in chunks] == [
        MIN_CHUNK_SIZE_WORDS,
        MIN_CHUNK_SIZE_WORDS,
    ]
    assert chunks[0].text.split()[-MIN_OVERLAP_WORDS:] == chunks[1].text.split()[:MIN_OVERLAP_WORDS]


def test_split_text_into_chunks_accepts_maximum_size_and_overlap() -> None:
    chunks = split_text_into_chunks(
        _make_words(1_400),
        chunk_size_words=MAX_CHUNK_SIZE_WORDS,
        overlap_words=MAX_OVERLAP_WORDS,
    )

    assert len(chunks) == 2
    assert chunks[0].word_count == 750
    assert chunks[1].word_count == MAX_CHUNK_SIZE_WORDS
    assert chunks[0].text.split()[-MAX_OVERLAP_WORDS:] == chunks[1].text.split()[:MAX_OVERLAP_WORDS]


def test_split_text_into_chunks_keeps_final_pair_inside_size_limits() -> None:
    chunks = split_text_into_chunks(
        _make_words(1_376),
        chunk_size_words=700,
        overlap_words=125,
    )

    assert len(chunks) == 2
    assert all(MIN_CHUNK_SIZE_WORDS <= chunk.word_count <= MAX_CHUNK_SIZE_WORDS for chunk in chunks)
    overlap = len(set(chunks[0].text.split()) & set(chunks[1].text.split()))
    assert MIN_OVERLAP_WORDS <= overlap <= MAX_OVERLAP_WORDS


def test_split_text_into_chunks_estimates_page_ranges() -> None:
    chunks = split_text_into_chunks(
        _make_words(1_250),
        section_name="Results",
        page_count=5,
        chunk_size_words=500,
        overlap_words=100,
    )

    assert [(chunk.page_start, chunk.page_end) for chunk in chunks] == [
        (1, 2),
        (2, 4),
        (4, 5),
    ]


def test_split_text_into_chunks_validates_chunk_size_and_overlap() -> None:
    with pytest.raises(ValueError, match="between 500 and 800"):
        split_text_into_chunks(_make_words(600), chunk_size_words=499)

    with pytest.raises(ValueError, match="between 100 and 150"):
        split_text_into_chunks(_make_words(600), overlap_words=99)

    with pytest.raises(ValueError, match="between 500 and 800"):
        split_text_into_chunks(_make_words(900), chunk_size_words=801)

    with pytest.raises(ValueError, match="between 100 and 150"):
        split_text_into_chunks(_make_words(900), overlap_words=151)


def test_split_sections_into_chunks_preserves_section_names_and_indexes() -> None:
    text = f"""Research Title

Abstract
{_make_words(520, "abstract")}

Introduction
{_make_words(520, "intro")}
"""
    sections = detect_sections(text)

    chunks = split_sections_into_chunks(
        sections,
        page_count=4,
        chunk_size_words=500,
        overlap_words=100,
    )

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert chunks[0].section_name == "Title"
    assert chunks[1].section_name == "Abstract"
    assert chunks[2].section_name == "Introduction"
    assert all(chunk.text for chunk in chunks)
    assert all(chunk.page_start is not None for chunk in chunks)


def test_split_sections_into_chunks_returns_empty_list_for_empty_sections() -> None:
    assert split_sections_into_chunks([]) == []


def test_text_chunk_serializes_to_dictionary() -> None:
    chunk = TextChunk(
        chunk_index=3,
        section_name="Discussion",
        page_start=4,
        page_end=5,
        text="source text",
        word_count=2,
    )

    assert chunk.to_dict() == {
        "chunk_index": 3,
        "section_name": "Discussion",
        "page_start": 4,
        "page_end": 5,
        "text": "source text",
        "word_count": 2,
    }


def test_replace_document_chunks_deletes_old_chunks_and_inserts_new_chunks(
    workspace_tmp_path,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings)
        session.add(
            Chunk(
                document_id=document.id,
                chunk_index=0,
                section_name="Old",
                text="old chunk",
                word_count=2,
            )
        )
        session.commit()

        persisted_chunks = replace_document_chunks(
            session,
            document.id,
            [
                TextChunk(
                    chunk_index=0,
                    section_name="Abstract",
                    page_start=1,
                    page_end=2,
                    text="new abstract chunk",
                    word_count=3,
                ),
                TextChunk(
                    chunk_index=1,
                    section_name="Introduction",
                    page_start=2,
                    page_end=3,
                    text="new introduction chunk",
                    word_count=3,
                ),
            ],
        )

        assert [chunk.chunk_index for chunk in persisted_chunks] == [0, 1]
        assert [chunk.section_name for chunk in persisted_chunks] == [
            "Abstract",
            "Introduction",
        ]
        assert [chunk.text for chunk in persisted_chunks] == [
            "new abstract chunk",
            "new introduction chunk",
        ]
        assert session.query(Chunk).filter_by(document_id=document.id).count() == 2

    database_engine.dispose()


def test_replace_document_chunks_can_clear_existing_chunks(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings)
        replace_document_chunks(
            session,
            document.id,
            [
                TextChunk(
                    chunk_index=0,
                    section_name="Abstract",
                    page_start=None,
                    page_end=None,
                    text="temporary chunk",
                    word_count=2,
                )
            ],
        )

        persisted_chunks = replace_document_chunks(session, document.id, [])

        assert persisted_chunks == []
        assert session.query(Chunk).filter_by(document_id=document.id).count() == 0

    database_engine.dispose()


def test_replace_document_chunks_rolls_back_when_database_commit_fails(
    workspace_tmp_path,
    monkeypatch,
) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        document = _create_document(session, settings)
        original_chunks = replace_document_chunks(
            session,
            document.id,
            [
                TextChunk(
                    chunk_index=0,
                    section_name="Original",
                    page_start=1,
                    page_end=1,
                    text="original chunk",
                    word_count=2,
                )
            ],
        )

        def fail_commit() -> None:
            raise SQLAlchemyError("commit failed")

        monkeypatch.setattr(session, "commit", fail_commit)

        with pytest.raises(ChunkPersistenceError, match="Could not replace document chunks"):
            replace_document_chunks(
                session,
                document.id,
                [
                    TextChunk(
                        chunk_index=0,
                        section_name="Replacement",
                        page_start=1,
                        page_end=2,
                        text="replacement chunk",
                        word_count=2,
                    )
                ],
            )

        persisted_chunks = session.query(Chunk).filter_by(document_id=document.id).all()
        assert len(persisted_chunks) == 1
        assert persisted_chunks[0].id == original_chunks[0].id
        assert persisted_chunks[0].text == "original chunk"

    database_engine.dispose()


def test_replace_document_chunks_rejects_invalid_document_id(workspace_tmp_path) -> None:
    session_factory, database_engine, _ = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        with pytest.raises(ValueError, match="positive integer"):
            replace_document_chunks(session, 0, [])

    database_engine.dispose()
