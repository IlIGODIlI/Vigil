from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.base import PaginatedResponse


class CommitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    sha: str
    message: str
    author_login: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    committed_at: Optional[datetime] = None
    parent_sha: Optional[str] = None
    created_at: datetime


class CommitListResponse(PaginatedResponse):
    items: List[CommitRead]
