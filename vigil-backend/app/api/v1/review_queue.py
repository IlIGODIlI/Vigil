import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review_queue import ReviewQueueItem, ReviewQueueListResponse
from app.services.review_queue_service import review_queue_service

router = APIRouter(prefix="/review-queue", tags=["Review Queue"])


@router.get(
    "",
    response_model=ReviewQueueListResponse,
    summary="List review queue items",
    description="Return active review queue items derived from pull requests and analyses.",
)
@router.get(
    "/",
    response_model=ReviewQueueListResponse,
    include_in_schema=False,
)
def get_review_queue(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ReviewQueueListResponse:
    return review_queue_service.get_review_queue(db=db, page=page, page_size=page_size)


@router.get(
    "/{pull_request_id}",
    response_model=ReviewQueueItem,
    summary="Get review queue item by PR ID",
    description="Return queue information for a specific pull request.",
)
def get_review_queue_item(
    pull_request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    return review_queue_service.get_review_queue_item(db=db, pull_request_id=pull_request_id)
