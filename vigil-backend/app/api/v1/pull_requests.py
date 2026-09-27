import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.github.client import github_client
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.analysis import AnalysisRead
from app.schemas.pull_request import PullRequestListResponse, PullRequestRead
from app.services.pull_request_service import pull_request_service

router = APIRouter(tags=["Pull Requests"])


@router.get(
    "/repositories/{repository_id}/pull-requests",
    response_model=PullRequestListResponse,
    summary="List pull requests for a repository",
    description="Return pull requests belonging to a repository, syncing from GitHub if installation_id is provided.",
)
async def list_pull_requests(
    repository_id: uuid.UUID,
    installation_id: Optional[int] = Query(None, description="GitHub App Installation ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PullRequestListResponse:
    if installation_id is not None:
        repo = db.scalar(select(Repository).where(Repository.id == repository_id))
        if repo:
            try:
                prs_data = await github_client.get_repository_pull_requests(
                    installation_id=installation_id,
                    owner=repo.owner_login,
                    repo=repo.name,
                    state="all",
                )
                pull_request_service.sync_repository_pull_requests(db=db, repository=repo, prs_data=prs_data)
            except Exception:
                pass

    return pull_request_service.get_pull_requests_for_repository(
        db=db, repository_id=repository_id, page=page, page_size=page_size
    )


@router.get(
    "/pull-requests/{pull_request_id}",
    response_model=PullRequestRead,
    summary="Get pull request details",
    description="Return details of a pull request by its internal UUID, syncing from GitHub if installation_id is provided.",
)
async def get_pull_request(
    pull_request_id: uuid.UUID,
    installation_id: Optional[int] = Query(None, description="GitHub App Installation ID"),
    db: Session = Depends(get_db),
) -> PullRequestRead:
    if installation_id is not None:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if pr and pr.repository:
            try:
                pr_data = await github_client.get_pull_request(
                    installation_id=installation_id,
                    owner=pr.repository.owner_login,
                    repo=pr.repository.name,
                    pr_number=pr.pr_number,
                )
                pull_request_service.sync_pull_request_payload(db=db, repository=pr.repository, pr_data=pr_data)
            except Exception:
                pass

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
