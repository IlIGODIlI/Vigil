import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.commit import Commit


class CommitAnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CommitAnalysisOverallStatus(str, Enum):
    NO_SIGNIFICANT_GAPS = "NO_SIGNIFICANT_GAPS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CommitAnalysis(Base):
    __tablename__ = "commit_analyses"
    __table_args__ = (
        Index("ix_commit_analyses_commit_id", "commit_id"),
        Index("ix_commit_analyses_status", "status"),
        Index("ix_commit_analyses_overall_status", "overall_status"),
        Index("ix_commit_analyses_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    commit_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("commits.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    overall_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    implementation_notes: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    testing_notes: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    error_handling_notes: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    documentation_notes: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    placeholder_notes: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    signals: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    commit: Mapped["Commit"] = relationship(
        "Commit",
        back_populates="commit_analyses",
    )
