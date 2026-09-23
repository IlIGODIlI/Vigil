import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.pull_request import PullRequest
    from app.models.review import Review


class AnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnalysisTrigger(str, Enum):
    WEBHOOK = "WEBHOOK"
    MANUAL = "MANUAL"


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_pull_request_id", "pull_request_id"),
        Index("ix_analyses_status", "status"),
        Index("ix_analyses_created_at", "created_at"),
        Index("ix_analyses_head_sha", "head_sha"),
        Index("ix_analyses_pull_request_id_created_at", "pull_request_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("pull_requests.id"),
        nullable=False,
    )
    head_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest",
        back_populates="analyses",
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding",
        back_populates="analysis",
    )
    review: Mapped[Optional["Review"]] = relationship(
        "Review",
        uselist=False,
        back_populates="analysis",
    )
