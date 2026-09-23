from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    source: str
    category: str
    severity: str
    rule_id: Optional[str] = None
    fingerprint: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    message: str
    status: str
    evidence: Optional[Dict[str, Any]] = None
    raw_artifact_uri: Optional[str] = None
    created_at: datetime


class FindingListResponse(PaginatedResponse):
    items: List[FindingRead]
