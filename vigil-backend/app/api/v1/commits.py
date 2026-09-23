import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.commit import CommitListResponse, CommitRead
from app.schemas.commit_analysis import CommitAnalysisRead
from app.services.commit_service import commit_service

router = APIRouter(tags=["Commits"])


@router.get(
    "/pull-requests/{pull_request_id}/commits",
    response_model=CommitListResponse,
    summary="List commits for a pull request",
    description="Return commits belonging to a pull request.",
)
def list_commits_for_pull_request(
    pull_request_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> CommitListResponse:
    return commit_service.get_commits_for_pull_request(
        db=db, pull_request_id=pull_request_id, page=page, page_size=page_size
    )


@router.get(
    "/commits/{sha}",
    response_model=CommitRead,
    summary="Get commit details",
    description="Return commit details by commit SHA.",
)
def get_commit(
    sha: str,
    db: Session = Depends(get_db),
) -> CommitRead:
    return commit_service.get_commit_by_sha(db=db, sha=sha)


@router.post(
    "/commits/{sha}/analyze",
    response_model=CommitAnalysisRead,
    summary="Trigger commit completeness analysis",
    description="Queue commit completeness analysis for a commit SHA.",
)
def trigger_commit_analysis(
    sha: str,
    db: Session = Depends(get_db),
) -> CommitAnalysisRead:
    return commit_service.trigger_commit_analysis(db=db, sha=sha)
