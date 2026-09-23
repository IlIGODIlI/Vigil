import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.commit import Commit
    from app.models.repository import Repository


class PullRequestStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


# Association table for PullRequest N:M Commit
pull_request_commits = Table(
    "pull_request_commits",
    Base.metadata,
    Column(
        "pull_request_id",
        UNIQUEIDENTIFIER,
        ForeignKey("pull_requests.id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "commit_id",
        UNIQUEIDENTIFIER,
        ForeignKey("commits.id"),
        primary_key=True,
        nullable=False,
    ),
    Column("position", Integer, nullable=True),
    Index("ix_pull_request_commits_pull_request_id", "pull_request_id"),
    Index("ix_pull_request_commits_commit_id", "commit_id"),
)


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "github_pr_id",
            name="uq_pull_requests_repository_github_pr",
        ),
        UniqueConstraint(
            "repository_id",
            "pr_number",
            name="uq_pull_requests_repository_pr_number",
        ),
        Index("ix_pull_requests_repository_id", "repository_id"),
        Index("ix_pull_requests_status", "status"),
        Index("ix_pull_requests_head_sha", "head_sha"),
        Index("ix_pull_requests_author_login", "author_login"),
        Index("ix_pull_requests_created_at", "created_at"),
        Index("ix_pull_requests_updated_at", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("repositories.id"),
        nullable=False,
    )
    github_pr_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    pr_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    author_login: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    head_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    base_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
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
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="pull_requests",
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="pull_request",
    )
    commits: Mapped[List["Commit"]] = relationship(
        "Commit",
        secondary=pull_request_commits,
        back_populates="pull_requests",
    )
