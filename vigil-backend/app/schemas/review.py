from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    status: str
    summary: Optional[str] = None
    review_body: Optional[str] = None
    github_review_id: Optional[int] = None
    github_review_url: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReviewListResponse(PaginatedResponse):
    items: List[ReviewRead]
