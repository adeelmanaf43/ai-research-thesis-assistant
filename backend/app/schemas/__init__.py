"""API schema package."""

from backend.app.schemas.document import (
    DocumentCreate,
    DocumentLocalAnalysisResponse,
    DocumentMetadataUpdate,
    DocumentOverviewResponse,
    DocumentResponse,
    DocumentSectionSummariesResponse,
    ProcessingSummaryResponse,
    SectionOverviewResponse,
    SectionSummaryResponse,
)
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
    "DocumentLocalAnalysisResponse",
    "DocumentMetadataUpdate",
    "DocumentOverviewResponse",
    "DocumentResponse",
    "DocumentSectionSummariesResponse",
    "HealthResponse",
    "ProcessingSummaryResponse",
    "ProjectCreate",
    "ProjectDetailResponse",
    "ProjectListItem",
    "ProjectResponse",
    "ProjectUpdate",
    "SectionOverviewResponse",
    "SectionSummaryResponse",
]
