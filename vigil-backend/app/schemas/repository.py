from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.base import PaginatedResponse


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    github_repo_id: int
    owner_login: str
    name: str
    full_name: str
    default_branch: str
    private: bool
    html_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(PaginatedResponse):
    items: List[RepositoryRead]
