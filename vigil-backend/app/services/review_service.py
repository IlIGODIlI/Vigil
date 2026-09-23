import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.models.pull_request import PullRequest
from app.models.review import Review
from app.schemas.review import ReviewRead


class ReviewService:
    @staticmethod
    def get_review_for_pull_request(db: Session, pull_request_id: uuid.UUID) -> ReviewRead:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        # Sort analyses by creation date descending to find the latest review
        analyses = sorted(pr.analyses, key=lambda a: a.created_at, reverse=True)
        for analysis in analyses:
            if analysis.review:
                return ReviewRead.model_validate(analysis.review)

        raise ResourceNotFoundException(f"No review found for pull request with ID '{pull_request_id}'")


review_service = ReviewService()
