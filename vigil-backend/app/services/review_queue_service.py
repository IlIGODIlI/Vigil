import uuid
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis, AnalysisStatus
from app.models.pull_request import PullRequest
from app.models.review import Review, ReviewStatus
from app.schemas.pull_request import PullRequestRead
from app.schemas.review_queue import ReviewQueueItem, ReviewQueueListResponse


class ReviewQueueService:
    @staticmethod
    def get_review_queue(db: Session, page: int = 1, page_size: int = 20) -> ReviewQueueListResponse:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Get all PRs
        all_prs = list(db.scalars(select(PullRequest)).all())
        queue_items: List[ReviewQueueItem] = []

        for pr in all_prs:
            latest_analysis = (
                sorted(pr.analyses, key=lambda a: a.created_at, reverse=True)[0]
                if pr.analyses
                else None
            )
            latest_review = latest_analysis.review if latest_analysis else None

            # Include if in queue state
            in_queue = False
            if latest_analysis:
                if latest_analysis.status in (AnalysisStatus.QUEUED.value, AnalysisStatus.RUNNING.value):
                    in_queue = True
                elif latest_analysis.status == AnalysisStatus.COMPLETED.value:
                    if not latest_review or latest_review.status in (ReviewStatus.DRAFT.value, ReviewStatus.READY.value):
                        in_queue = True

            if in_queue and latest_analysis:
                queue_items.append(
                    ReviewQueueItem(
                        pull_request=PullRequestRead.model_validate(pr),
                        latest_analysis_id=latest_analysis.id,
                        latest_analysis_status=latest_analysis.status,
                        latest_review_id=latest_review.id if latest_review else None,
                        latest_review_status=latest_review.status if latest_review else None,
                        queued_at=latest_analysis.created_at,
                    )
                )

        total = len(queue_items)
        offset = (page - 1) * page_size
        items = queue_items[offset : offset + page_size]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ReviewQueueListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_review_queue_item(db: Session, pull_request_id: uuid.UUID) -> ReviewQueueItem:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        latest_analysis = (
            sorted(pr.analyses, key=lambda a: a.created_at, reverse=True)[0]
            if pr.analyses
            else None
        )
        latest_review = latest_analysis.review if latest_analysis else None

        return ReviewQueueItem(
            pull_request=PullRequestRead.model_validate(pr),
            latest_analysis_id=latest_analysis.id if latest_analysis else None,
            latest_analysis_status=latest_analysis.status if latest_analysis else None,
            latest_review_id=latest_review.id if latest_review else None,
            latest_review_status=latest_review.status if latest_review else None,
            queued_at=latest_analysis.created_at if latest_analysis else pr.created_at,
        )


review_queue_service = ReviewQueueService()
