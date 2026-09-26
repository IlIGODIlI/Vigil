"""
Phase 6 — Finding Verification API Routes.

Endpoints:
  GET  /api/v1/findings/{finding_id}          — Finding detail (reviewer view)
  POST /api/v1/findings/{finding_id}/verify   — Submit verification decision
  GET  /api/v1/findings/{finding_id}/history  — Verification history (audit)

Authentication: X-Reviewer-Login header (enforced via get_current_reviewer dependency).

GitHub publishing: NOT implemented in this phase.
Automatic decisions: NOT implemented. Human reviewer required.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import ReviewerContext, get_current_reviewer
from app.db.session import get_db
from app.schemas.finding_detail import FindingDetail, VerifyFindingRequest
from app.schemas.finding_verification import FindingVerificationList
from app.services.finding_verification_service import finding_verification_service

router = APIRouter(tags=["Findings"])


@router.get(
    "/findings/{finding_id}",
    response_model=FindingDetail,
    summary="Get finding detail",
    description=(
        "Return full finding detail for reviewer inspection. "
        "Includes AI evidence (read-only), analysis context, and verification history."
    ),
)
def get_finding_detail(
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
    reviewer: ReviewerContext = Depends(get_current_reviewer),
) -> FindingDetail:
    return finding_verification_service.get_finding_detail(
        db=db,
        finding_id=finding_id,
    )


@router.post(
    "/findings/{finding_id}/verify",
    response_model=FindingDetail,
    summary="Submit verification decision",
    description=(
        "Submit a human reviewer decision for a finding. "
        "Decision must be one of: VERIFIED, REJECTED, DISMISSED. "
        "The original AI-generated evidence is never modified. "
        "Each decision is recorded in the audit trail. "
        "This endpoint does NOT publish anything to GitHub."
    ),
)
def verify_finding(
    finding_id: uuid.UUID,
    request: VerifyFindingRequest,
    expected_status: Optional[str] = Query(
        None,
        description=(
            "Optional: the current finding status the caller observed. "
            "If the status has changed since then the request will be rejected "
            "(optimistic concurrency guard)."
        ),
    ),
    db: Session = Depends(get_db),
    reviewer: ReviewerContext = Depends(get_current_reviewer),
) -> FindingDetail:
    return finding_verification_service.verify_finding(
        db=db,
        finding_id=finding_id,
        decision=request.decision,
        reviewer=reviewer,
        comment=request.comment,
        expected_current_status=expected_status,
    )


@router.get(
    "/findings/{finding_id}/history",
    response_model=FindingVerificationList,
    summary="Get verification history",
    description=(
        "Return the complete, ordered audit trail of human verification "
        "decisions for a specific finding. Records are append-only."
    ),
)
def get_finding_history(
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
    reviewer: ReviewerContext = Depends(get_current_reviewer),
) -> FindingVerificationList:
    return finding_verification_service.get_verification_history(
        db=db,
        finding_id=finding_id,
    )
