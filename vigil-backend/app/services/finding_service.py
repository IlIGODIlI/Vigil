import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.models.pull_request import PullRequest
from app.models.finding import Finding
from app.schemas.finding import FindingListResponse, FindingRead


class FindingService:
    @staticmethod
    def get_findings_for_pull_request(
        db: Session,
        pull_request_id: uuid.UUID,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FindingListResponse:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        analysis_ids = [a.id for a in pr.analyses]
        if not analysis_ids:
            return FindingListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

        stmt = select(Finding).where(Finding.analysis_id.in_(analysis_ids))
        if severity:
            stmt = stmt.where(Finding.severity == severity.upper())
        if status:
            stmt = stmt.where(Finding.status == status.upper())
        if source:
            stmt = stmt.where(Finding.source == source.upper())

        all_findings = list(db.scalars(stmt).all())
        total = len(all_findings)
        items = all_findings[offset : offset + page_size]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return FindingListResponse(
            items=[FindingRead.model_validate(f) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


finding_service = FindingService()
