import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.pull_request import pull_request_commits

if TYPE_CHECKING:
    from app.models.commit_analysis import CommitAnalysis
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "sha",
            name="uq_commits_repository_sha",
        ),
        Index("ix_commits_repository_id", "repository_id"),
        Index("ix_commits_sha", "sha"),
        Index("ix_commits_committed_at", "committed_at"),
        Index("ix_commits_author_login", "author_login"),
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
    sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    author_login: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    author_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    author_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    committed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    parent_sha: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="commits",
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest",
        secondary=pull_request_commits,
        back_populates="commits",
    )
    commit_analyses: Mapped[List["CommitAnalysis"]] = relationship(
        "CommitAnalysis",
        back_populates="commit",
    )
