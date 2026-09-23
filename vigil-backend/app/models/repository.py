import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.pull_request import PullRequest
    from app.models.user import User


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("github_repo_id", name="uq_repositories_github_repo_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    github_repo_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    owner_login: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
    )
    default_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    html_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="repositories",
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="repository",
    )
    commits: Mapped[List["Commit"]] = relationship(
        "Commit",
        back_populates="repository",
    )
