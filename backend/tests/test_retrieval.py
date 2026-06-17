import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_database_engine, get_session_factory, init_database
from backend.app.models.chunk import Chunk
from backend.app.schemas.document import DocumentCreate
from backend.app.schemas.project import ProjectCreate
from backend.app.services.document_service import create_document_record, save_uploaded_file
from backend.app.services.project_service import create_project
from backend.app.services.retrieval import RetrievalResult, search_chunks


def _session_factory(workspace_tmp_path):
    database_path = workspace_tmp_path / "retrieval.db"
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


def _create_document_with_chunks(session, settings, filename: str, chunks: list[Chunk]):
    project = create_project(session, ProjectCreate(name=f"{filename} project"))
    saved_file = save_uploaded_file(settings.upload_dir, project.id, filename, b"content")
    document = create_document_record(
        session,
        DocumentCreate(project_id=project.id, original_filename=filename),
        saved_file.stored_filename,
        saved_file.file_path,
        status="processed",
    )
    for chunk in chunks:
        chunk.document_id = document.id
        session.add(chunk)
    session.commit()
    return document


def _chunk(
    chunk_index: int,
    text: str,
    *,
    section_name: str = "Unknown",
    page_start: int | None = 1,
    page_end: int | None = 1,
) -> Chunk:
    return Chunk(
        document_id=0,
        chunk_index=chunk_index,
        section_name=section_name,
        text=text,
        word_count=len(text.split()),
        page_start=page_start,
        page_end=page_end,
    )


def test_search_chunks_returns_ranked_results_with_source_metadata(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "retrieval-paper.pdf",
            [
                _chunk(
                    0,
                    "Local retrieval improves thesis citation tracking and source review.",
                    section_name="Introduction",
                    page_start=1,
                    page_end=2,
                ),
                _chunk(
                    1,
                    "The methodology used retrieval interviews with postgraduate thesis writers.",
                    section_name="Methodology",
                    page_start=3,
                    page_end=4,
                ),
                _chunk(
                    2,
                    "Export formatting creates report files for later milestones.",
                    section_name="Conclusion",
                    page_start=5,
                    page_end=5,
                ),
            ],
        )

        results = search_chunks(session, "citation tracking retrieval", top_k=2)

    database_engine.dispose()

    assert len(results) == 2
    assert isinstance(results[0], RetrievalResult)
    assert results[0].chunk_index == 0
    assert results[0].section_name == "Introduction"
    assert results[0].page_start == 1
    assert results[0].page_end == 2
    assert results[0].score > results[1].score
    assert "citation tracking" in results[0].text
    assert results[0].to_dict()["chunk_id"] == results[0].chunk_id
    assert results[0].to_response_dict()["full_text"] is None


def test_search_chunks_ranks_most_relevant_academic_chunk_first(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "academic-relevance-paper.pdf",
            [
                _chunk(
                    0,
                    "The introduction describes thesis writing and broad research goals.",
                    section_name="Introduction",
                ),
                _chunk(
                    1,
                    "The methodology used a survey sample of postgraduate students "
                    "and interview responses from thesis writers.",
                    section_name="Methodology",
                ),
                _chunk(
                    2,
                    "The conclusion recommends future reporting workflows.",
                    section_name="Conclusion",
                ),
            ],
        )

        results = search_chunks(session, "methodology survey sample", top_k=3)

    database_engine.dispose()

    assert results
    assert results[0].section_name == "Methodology"
    assert "survey sample" in results[0].text
    assert results[0].score > 0


def test_search_chunks_boosts_exact_academic_phrases(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "phrase-paper.pdf",
            [
                _chunk(
                    0,
                    "Citation tracking appears in this paragraph. "
                    "Retrieval is discussed in another unrelated paragraph.",
                    section_name="Introduction",
                ),
                _chunk(
                    1,
                    "The system improves citation tracking retrieval for thesis writers.",
                    section_name="Results",
                ),
            ],
        )

        results = search_chunks(session, "citation tracking retrieval", top_k=2)

    database_engine.dispose()

    assert results[0].section_name == "Results"
    assert results[0].score > results[1].score


def test_search_chunks_filters_by_document_id(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        first_document = _create_document_with_chunks(
            session,
            settings,
            "first-paper.pdf",
            [_chunk(0, "Retrieval finds evidence about local summaries.")],
        )
        second_document = _create_document_with_chunks(
            session,
            settings,
            "second-paper.pdf",
            [_chunk(0, "Retrieval finds evidence about methodology design.")],
        )

        results = search_chunks(session, "retrieval evidence", document_id=second_document.id)

    database_engine.dispose()

    assert results
    assert {result.document_id for result in results} == {second_document.id}
    assert first_document.id not in {result.document_id for result in results}


def test_search_chunks_respects_top_k(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "ranked-paper.pdf",
            [
                _chunk(0, "Raremethod retrieval citation evidence."),
                _chunk(1, "Retrieval citation evidence."),
                _chunk(2, "Retrieval evidence."),
            ],
        )

        results = search_chunks(session, "raremethod citation", top_k=1)

    database_engine.dispose()

    assert len(results) == 1
    assert results[0].chunk_index == 0


def test_search_chunks_returns_empty_list_when_no_chunks_match(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "unmatched-paper.pdf",
            [_chunk(0, "Methodology survey participants analysis.")],
        )

        results = search_chunks(session, "quantum astrophysics")

    database_engine.dispose()

    assert results == []


def test_search_chunks_returns_empty_list_when_no_chunks_exist(workspace_tmp_path) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        results = search_chunks(session, "retrieval")

    database_engine.dispose()

    assert results == []


def test_search_chunks_returns_empty_list_for_missing_document_filter(workspace_tmp_path) -> None:
    session_factory, database_engine, settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        _create_document_with_chunks(
            session,
            settings,
            "existing-paper.pdf",
            [_chunk(0, "Retrieval evidence exists for a different document.")],
        )

        results = search_chunks(session, "retrieval evidence", document_id=999)

    database_engine.dispose()

    assert results == []


@pytest.mark.parametrize(
    ("query", "top_k", "document_id", "message"),
    [
        ("   ", 5, None, "Search query"),
        ("retrieval", 0, None, "top_k"),
        ("retrieval", 11, None, "top_k"),
        ("retrieval", 5, 0, "Document ID"),
    ],
)
def test_search_chunks_validates_inputs(
    workspace_tmp_path,
    query: str,
    top_k: int,
    document_id: int | None,
    message: str,
) -> None:
    session_factory, database_engine, _settings = _session_factory(workspace_tmp_path)

    with session_factory() as session:
        with pytest.raises(ValueError, match=message):
            search_chunks(session, query, top_k=top_k, document_id=document_id)

    database_engine.dispose()


def test_retrieval_result_response_dict_uses_preview_without_full_text() -> None:
    result = RetrievalResult(
        chunk_id=7,
        document_id=3,
        chunk_index=2,
        section_name="Results",
        page_start=8,
        page_end=9,
        score=0.82,
        text=" ".join(["retrieval evidence"] * 30),
    )

    payload = result.to_response_dict(preview_char_limit=60)

    assert payload == {
        "chunk_id": 7,
        "chunk_index": 2,
        "section_name": "Results",
        "page_start": 8,
        "page_end": 9,
        "score": 0.82,
        "text_preview": "retrieval evidence retrieval evidence retrieval evidence...",
        "full_text": None,
    }


def test_retrieval_result_response_dict_can_include_full_text() -> None:
    result = RetrievalResult(
        chunk_id=8,
        document_id=3,
        chunk_index=0,
        section_name=None,
        page_start=None,
        page_end=None,
        score=0.5,
        text="Full chunk text.",
    )

    payload = result.to_response_dict(include_full_text=True)

    assert payload["text_preview"] == "Full chunk text."
    assert payload["full_text"] == "Full chunk text."


def test_retrieval_result_response_dict_rejects_invalid_preview_limit() -> None:
    result = RetrievalResult(
        chunk_id=8,
        document_id=3,
        chunk_index=0,
        section_name=None,
        page_start=None,
        page_end=None,
        score=0.5,
        text="Full chunk text.",
    )

    with pytest.raises(ValueError, match="Preview character limit"):
        result.to_response_dict(preview_char_limit=0)
