import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.repository import Repository
from app.models.user import User
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

    @staticmethod
    def _get_or_create_user(
        db: Session, owner_login: str, owner_id: Optional[int] = None
    ) -> User:
        stmt = select(User).where(User.github_login == owner_login)
        user = db.scalar(stmt)
        if not user and owner_id:
            user = db.scalar(select(User).where(User.github_user_id == owner_id))

        if not user:
            user = User(
                id=uuid.uuid4(),
                github_user_id=owner_id or 0,
                github_login=owner_login,
                display_name=owner_login,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    @classmethod
    def sync_repository_payload(cls, db: Session, repo_data: dict) -> Repository:
        """Upsert a repository record idempotently from a GitHub API payload or webhook."""
        github_repo_id = repo_data.get("id")
        if not github_repo_id:
            raise ValueError("Missing repository ID in GitHub payload")

        owner_raw = repo_data.get("owner", {})
        owner_login = (
            owner_raw.get("login") if isinstance(owner_raw, dict) else repo_data.get("owner_login", "unknown")
        ) or "unknown"
        owner_id = owner_raw.get("id") if isinstance(owner_raw, dict) else None

        name = repo_data.get("name", "")
        full_name = repo_data.get("full_name") or f"{owner_login}/{name}"
        default_branch = repo_data.get("default_branch") or "main"
        private = bool(repo_data.get("private", False))
        html_url = repo_data.get("html_url") or f"https://github.com/{full_name}"

        repo = db.scalar(select(Repository).where(Repository.github_repo_id == github_repo_id))
        now = datetime.now(timezone.utc)

        if repo:
            repo.name = name
            repo.full_name = full_name
            repo.owner_login = owner_login
            repo.default_branch = default_branch
            repo.private = private
            repo.html_url = html_url
            repo.is_active = True
            repo.updated_at = now
        else:
            user = cls._get_or_create_user(db, owner_login=owner_login, owner_id=owner_id)
            repo = Repository(
                id=uuid.uuid4(),
                user_id=user.id,
                github_repo_id=github_repo_id,
                owner_login=owner_login,
                name=name,
                full_name=full_name,
                default_branch=default_branch,
                private=private,
                html_url=html_url,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(repo)

        db.commit()
        db.refresh(repo)
        return repo

    @classmethod
    def sync_installation_repositories(
        cls, db: Session, repos_data: List[dict]
    ) -> List[Repository]:
        """Upsert a list of GitHub repository payloads."""
        synced_repos: List[Repository] = []
        for repo_data in repos_data:
            if isinstance(repo_data, dict):
                repo = cls.sync_repository_payload(db, repo_data)
                synced_repos.append(repo)
        return synced_repos


repository_service = RepositoryService()
