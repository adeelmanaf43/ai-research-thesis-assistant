import re
from pathlib import Path, PurePosixPath
from uuid import uuid4

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
MAX_STEM_LENGTH = 120
MAX_EXTENSION_LENGTH = 20


class UnsafeStoragePathError(ValueError):
    """Raised when a storage path would escape the configured upload directory."""


def _validate_project_id(project_id: int) -> int:
    if isinstance(project_id, bool) or not isinstance(project_id, int) or project_id < 1:
        raise ValueError("project_id must be a positive integer.")
    return project_id


def _clean_filename_part(value: str, fallback: str) -> str:
    cleaned = SAFE_FILENAME_PATTERN.sub("_", value).strip("._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or fallback


def sanitize_upload_filename(filename: str) -> str:
    raw_filename = filename.strip().replace("\\", "/")
    if not raw_filename:
        raise ValueError("filename cannot be empty.")

    basename = PurePosixPath(raw_filename).name
    if basename in {"", ".", ".."}:
        raise ValueError("filename must contain a usable file name.")

    suffixes = PurePosixPath(basename).suffixes
    extension = ""
    if suffixes:
        last_suffix = suffixes[-1].lstrip(".")
        extension = _clean_filename_part(last_suffix, "").lower()[:MAX_EXTENSION_LENGTH]

    stem = basename[: -len(suffixes[-1])] if suffixes else basename
    safe_stem = _clean_filename_part(stem, "document")[:MAX_STEM_LENGTH]

    if extension:
        return f"{safe_stem}.{extension}"
    return safe_stem


def build_stored_document_filename(original_filename: str, unique_token: str | None = None) -> str:
    token = unique_token or uuid4().hex
    safe_token = _clean_filename_part(token, "document")
    return f"{safe_token}_{sanitize_upload_filename(original_filename)}"


def ensure_path_within_directory(path: Path, directory: Path) -> Path:
    resolved_path = path.resolve(strict=False)
    resolved_directory = directory.resolve(strict=False)
    if resolved_path != resolved_directory and resolved_directory not in resolved_path.parents:
        raise UnsafeStoragePathError("Storage path escaped the configured upload directory.")
    return resolved_path


def get_project_documents_dir(upload_dir: Path, project_id: int) -> Path:
    validated_project_id = _validate_project_id(project_id)
    directory = upload_dir / "projects" / str(validated_project_id) / "documents"
    return ensure_path_within_directory(directory, upload_dir)


def ensure_project_documents_dir(upload_dir: Path, project_id: int) -> Path:
    directory = get_project_documents_dir(upload_dir, project_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_document_storage_path(upload_dir: Path, project_id: int, stored_filename: str) -> Path:
    documents_dir = get_project_documents_dir(upload_dir, project_id)
    safe_filename = sanitize_upload_filename(stored_filename)
    return ensure_path_within_directory(documents_dir / safe_filename, documents_dir)
