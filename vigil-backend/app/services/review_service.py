import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.models.pull_request import PullRequest
from app.models.review import Review
from app.schemas.ai_review import AIReviewResponse
from app.schemas.review import ReviewRead
from app.services.ai.context.schemas import (
    ChangedFileContext,
    RepositoryStructureContext,
    ScannerFindingContext,
)


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

    @staticmethod
    async def execute_ai_review(
        db: Session,
        pull_request_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        persist: bool = False,
        analysis_id: Optional[uuid.UUID] = None,
        changed_files: Optional[List[ChangedFileContext]] = None,
        scanner_findings: Optional[List[ScannerFindingContext]] = None,
        repository_structure: Optional[RepositoryStructureContext] = None,
    ) -> AIReviewResponse:
        from app.services.ai_review_service import ai_review_service

        return await ai_review_service.review_pull_request(
            db=db,
            pull_request_id=pull_request_id,
            custom_instructions=custom_instructions,
            persist=persist,
            analysis_id=analysis_id,
            changed_files=changed_files,
            scanner_findings=scanner_findings,
            repository_structure=repository_structure,
        )


review_service = ReviewService()
