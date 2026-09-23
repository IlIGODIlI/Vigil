from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
