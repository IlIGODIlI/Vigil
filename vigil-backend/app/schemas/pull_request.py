from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse


class PullRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    github_pr_id: int
    pr_number: int
    title: str
    description: Optional[str] = None
    author_login: str
    source_branch: str
    target_branch: str
    head_sha: str
    base_sha: str
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None


class PullRequestListResponse(PaginatedResponse):
    items: List[PullRequestRead]
