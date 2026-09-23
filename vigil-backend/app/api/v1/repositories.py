import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.repository import RepositoryListResponse, RepositoryRead
from app.services.repository_service import repository_service

router = APIRouter(tags=["Repositories"])


@router.get(
    "/repositories",
    response_model=RepositoryListResponse,
    summary="List repositories",
    description="Return repositories stored in the Vigil database.",
)
def list_repositories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> RepositoryListResponse:
    return repository_service.get_repositories(db=db, page=page, page_size=page_size)


@router.get(
    "/repositories/{repository_id}",
    response_model=RepositoryRead,
    summary="Get repository",
    description="Return details of one repository by its internal UUID.",
)
def get_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RepositoryRead:
    return repository_service.get_repository_by_id(db=db, repository_id=repository_id)
