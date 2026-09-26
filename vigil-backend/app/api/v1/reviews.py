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
    response_model=ReviewRead,
    summary="Publish review to GitHub",
    description="Publish verified findings as a GitHub pull request review.",
)
async def publish_review(
    review_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReviewRead:
    return await review_service.publish_review(db=db, review_id=review_id)
