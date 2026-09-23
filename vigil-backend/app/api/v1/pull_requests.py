import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import AnalysisRead
from app.schemas.pull_request import PullRequestListResponse, PullRequestRead
from app.services.pull_request_service import pull_request_service

router = APIRouter(tags=["Pull Requests"])


@router.get(
    "/repositories/{repository_id}/pull-requests",
    response_model=PullRequestListResponse,
    summary="List pull requests for a repository",
    description="Return pull requests belonging to a repository.",
)
def list_pull_requests(
    repository_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PullRequestListResponse:
    return pull_request_service.get_pull_requests_for_repository(
        db=db, repository_id=repository_id, page=page, page_size=page_size
    )


@router.get(
    "/pull-requests/{pull_request_id}",
    response_model=PullRequestRead,
    summary="Get pull request details",
    description="Return details of a pull request by its internal UUID.",
)
def get_pull_request(
    pull_request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PullRequestRead:
    return pull_request_service.get_pull_request_by_id(db=db, pull_request_id=pull_request_id)


@router.post(
    "/pull-requests/{pull_request_id}/analyze",
    response_model=AnalysisRead,
    summary="Trigger pull request analysis",
    description="Queue a new analysis execution record for a pull request.",
)
def trigger_pull_request_analysis(
    pull_request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AnalysisRead:
    return pull_request_service.trigger_analysis(db=db, pull_request_id=pull_request_id)
