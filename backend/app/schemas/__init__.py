"""API schema package."""

from backend.app.schemas.document import DocumentCreate, DocumentMetadataUpdate, DocumentResponse
from backend.app.schemas.health import HealthResponse
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectResponse,
    ProjectUpdate,
)

__all__ = [
    "DocumentCreate",
    "DocumentMetadataUpdate",
    "DocumentResponse",
    "HealthResponse",
    "ProjectCreate",
    "ProjectDetailResponse",
    "ProjectListItem",
    "ProjectResponse",
    "ProjectUpdate",
]
