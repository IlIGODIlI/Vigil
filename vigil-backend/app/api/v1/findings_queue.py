"""
Phase 6 — Finding-centric Review Queue API Routes.

The Phase 6 queue is finding-centric (each item is a finding pending review),
replacing the old PR-centric queue logic.  The original PR-level queue
endpoints (GET /review-queue, GET /review-queue/{pull_request_id}) are
preserved for backward compatibility.

New endpoints:
  GET /api/v1/findings/queue          — Filterable, paginated findings queue

Authentication: X-Reviewer-Login header required.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import ReviewerContext, get_current_reviewer
from app.db.session import get_db
from app.schemas.finding_detail import FindingQueueListResponse
from app.services.finding_verification_service import finding_verification_service

router = APIRouter(tags=["Review Queue"])


@router.get(
    "/findings/queue",
    response_model=FindingQueueListResponse,
    summary="Review queue — findings pending human verification",
    description=(
        "Return the paginated, filterable queue of AI-generated findings "
        "that require human verification. "
        "Default ordering: severity (CRITICAL first), then oldest first. "
        "Filtering happens at the database level."
    ),
)
def get_findings_review_queue(
    status: Optional[str] = Query(
        None,
        description=(
            "Filter by finding status. "
            "Defaults to OPEN and PENDING_REVIEW (findings needing review)."
        ),
    ),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW, INFO"),
    repository_id: Optional[uuid.UUID] = Query(None, description="Filter by repository UUID"),
    pull_request_id: Optional[uuid.UUID] = Query(None, description="Filter by pull request UUID"),
    commit_sha: Optional[str] = Query(None, description="Filter by commit SHA"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
    reviewer: ReviewerContext = Depends(get_current_reviewer),
) -> FindingQueueListResponse:
    return finding_verification_service.get_review_queue(
        db=db,
        status=status,
        severity=severity,
        repository_id=repository_id,
        pull_request_id=pull_request_id,
        commit_sha=commit_sha,
        page=page,
        page_size=page_size,
    )
