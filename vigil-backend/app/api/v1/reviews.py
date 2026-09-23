import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review import ReviewRead
from app.services.review_service import review_service

router = APIRouter(tags=["Reviews"])


@router.get(
    "/pull-requests/{pull_request_id}/review",
    response_model=ReviewRead,
    summary="Get review for a pull request",
    description="Return the latest generated review for a pull request.",
)
def get_pull_request_review(
    pull_request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReviewRead:
    return review_service.get_review_for_pull_request(db=db, pull_request_id=pull_request_id)


@router.post(
    "/reviews/{review_id}/publish",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Publish review to GitHub",
    description="Publish review back to GitHub (Not Implemented - Phase 4).",
)
def publish_review(review_id: uuid.UUID) -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GitHub review publishing is not implemented yet (Phase 4 feature).",
    )
