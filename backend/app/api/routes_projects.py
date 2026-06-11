from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectUpdate,
)
from backend.app.services.project_service import (
    create_project,
    delete_project,
    get_project_by_id,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project_route(
    project_in: ProjectCreate, db: Session = Depends(get_db)
) -> ProjectDetailResponse:
    return create_project(db, project_in)


@router.get("", response_model=list[ProjectListItem])
def list_projects_route(db: Session = Depends(get_db)) -> list[ProjectListItem]:
    return list_projects(db)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project_route(project_id: int, db: Session = Depends(get_db)) -> ProjectDetailResponse:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
def update_project_route(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return update_project(db, project, project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_route(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    delete_project(db, project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
