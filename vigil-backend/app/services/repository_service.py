import uuid
from typing import List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.repository import Repository
from app.schemas.repository import RepositoryListResponse, RepositoryRead


class RepositoryService:
    @staticmethod
    def get_repositories(db: Session, page: int = 1, page_size: int = 20) -> RepositoryListResponse:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        total = db.scalar(select(func.count(Repository.id))) or 0
        stmt = select(Repository).order_by(Repository.created_at.desc()).offset(offset).limit(page_size)
        items = list(db.scalars(stmt).all())

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return RepositoryListResponse(
            items=[RepositoryRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_repository_by_id(db: Session, repository_id: uuid.UUID) -> RepositoryRead:
        repo = db.scalar(select(Repository).where(Repository.id == repository_id))
        if not repo:
            raise ResourceNotFoundException(f"Repository with ID '{repository_id}' not found")
        return RepositoryRead.model_validate(repo)


repository_service = RepositoryService()
