from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse
from app.schemas.pull_request import PullRequestRead


class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pull_request: PullRequestRead
    latest_analysis_id: Optional[uuid.UUID] = None
    latest_analysis_status: Optional[str] = None
    latest_review_id: Optional[uuid.UUID] = None
    latest_review_status: Optional[str] = None
    queued_at: Optional[datetime] = None


class ReviewQueueListResponse(PaginatedResponse):
    items: List[ReviewQueueItem]
