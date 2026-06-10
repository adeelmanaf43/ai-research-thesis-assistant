from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.project import Project
from backend.app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, project_in: ProjectCreate, user_id: int | None = None) -> Project:
    project = Project(
        name=project_in.name,
        description=project_in.description,
        user_id=user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, user_id: int | None = None) -> list[Project]:
    statement = select(Project).order_by(Project.created_at.desc(), Project.id.desc())
    if user_id is not None:
        statement = statement.where(Project.user_id == user_id)
    return list(db.scalars(statement).all())


def get_project_by_id(db: Session, project_id: int, user_id: int | None = None) -> Project | None:
    statement = select(Project).where(Project.id == project_id)
    if user_id is not None:
        statement = statement.where(Project.user_id == user_id)
    return db.scalars(statement).first()


def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()

