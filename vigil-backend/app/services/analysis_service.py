import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisRead


class AnalysisService:
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: uuid.UUID) -> AnalysisRead:
        analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        if not analysis:
            raise ResourceNotFoundException(f"Analysis with ID '{analysis_id}' not found")
        return AnalysisRead.model_validate(analysis)


analysis_service = AnalysisService()
