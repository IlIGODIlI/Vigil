import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import AnalysisRead
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.get(
    "/{analysis_id}",
    response_model=AnalysisRead,
    summary="Get analysis status/details",
    description="Return analysis execution details stored in the database.",
)
def get_analysis(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AnalysisRead:
    return analysis_service.get_analysis_by_id(db=db, analysis_id=analysis_id)
