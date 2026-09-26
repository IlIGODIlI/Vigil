from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.schemas.ai_review import AIReviewResponse
from app.schemas.analysis import AnalysisRead
from app.services.ai.context.schemas import (
    ChangedFileContext,
    RepositoryStructureContext,
    ScannerFindingContext,
)


class AnalysisService:
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: uuid.UUID) -> AnalysisRead:
        analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        if not analysis:
            raise ResourceNotFoundException(f"Analysis with ID '{analysis_id}' not found")
        return AnalysisRead.model_validate(analysis)

    @staticmethod
    async def execute_ai_review_for_analysis(
        db: Session,
        analysis_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        persist: bool = False,
        changed_files: Optional[List[ChangedFileContext]] = None,
        scanner_findings: Optional[List[ScannerFindingContext]] = None,
        repository_structure: Optional[RepositoryStructureContext] = None,
    ) -> AIReviewResponse:
        """Integration seam bridging an Analysis execution record to ReviewService.execute_ai_review."""
        analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        if not analysis:
            raise ResourceNotFoundException(f"Analysis with ID '{analysis_id}' not found")

        from app.services.review_service import review_service

        return await review_service.execute_ai_review(
            db=db,
            pull_request_id=analysis.pull_request_id,
            custom_instructions=custom_instructions,
            persist=persist,
            analysis_id=analysis.id,
            changed_files=changed_files,
            scanner_findings=scanner_findings,
            repository_structure=repository_structure,
        )


analysis_service = AnalysisService()
