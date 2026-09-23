from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse


class CommitAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commit_id: uuid.UUID
    status: str
    overall_status: str
    summary: Optional[str] = None
    implementation_notes: Optional[str] = None
    testing_notes: Optional[str] = None
    error_handling_notes: Optional[str] = None
    documentation_notes: Optional[str] = None
    placeholder_notes: Optional[str] = None
    signals: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class CommitAnalysisListResponse(PaginatedResponse):
    items: List[CommitAnalysisRead]
