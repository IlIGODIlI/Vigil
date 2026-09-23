import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.finding import FindingListResponse
from app.services.finding_service import finding_service

router = APIRouter(tags=["Findings"])


@router.get(
    "/pull-requests/{pull_request_id}/findings",
    response_model=FindingListResponse,
    summary="List findings for a pull request",
    description="Return findings associated with analyses of a pull request.",
)
def list_findings(
    pull_request_id: uuid.UUID,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> FindingListResponse:
    return finding_service.get_findings_for_pull_request(
        db=db,
        pull_request_id=pull_request_id,
        severity=severity,
        status=status,
        source=source,
        page=page,
        page_size=page_size,
    )
