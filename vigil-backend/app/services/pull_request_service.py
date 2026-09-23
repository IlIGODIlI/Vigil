import uuid
from typing import List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis, AnalysisStatus, AnalysisTrigger
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.analysis import AnalysisRead
from app.schemas.pull_request import PullRequestListResponse, PullRequestRead


class PullRequestService:
    @staticmethod
    def get_pull_requests_for_repository(
        db: Session, repository_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> PullRequestListResponse:
        repo = db.scalar(select(Repository).where(Repository.id == repository_id))
        if not repo:
            raise ResourceNotFoundException(f"Repository with ID '{repository_id}' not found")

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        total = db.scalar(
            select(func.count(PullRequest.id)).where(PullRequest.repository_id == repository_id)
        ) or 0
        stmt = (
            select(PullRequest)
            .where(PullRequest.repository_id == repository_id)
            .order_by(PullRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(db.scalars(stmt).all())

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return PullRequestListResponse(
            items=[PullRequestRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_pull_request_by_id(db: Session, pull_request_id: uuid.UUID) -> PullRequestRead:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")
        return PullRequestRead.model_validate(pr)

    @staticmethod
    def trigger_analysis(db: Session, pull_request_id: uuid.UUID) -> AnalysisRead:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        analysis = Analysis(
            pull_request_id=pr.id,
            head_sha=pr.head_sha,
            status=AnalysisStatus.QUEUED.value,
            trigger_type=AnalysisTrigger.MANUAL.value,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return AnalysisRead.model_validate(analysis)


pull_request_service = PullRequestService()
