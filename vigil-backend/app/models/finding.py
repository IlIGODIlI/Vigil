import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class FindingSource(str, Enum):
    SEMGREP = "SEMGREP"
    GITLEAKS = "GITLEAKS"
    TRIVY = "TRIVY"
    MS_SECURITY_DEVOPS = "MS_SECURITY_DEVOPS"
    AI_REVIEW = "AI_REVIEW"


class FindingCategory(str, Enum):
    SECURITY = "SECURITY"
    LOGIC = "LOGIC"
    ERROR_HANDLING = "ERROR_HANDLING"
    TESTING = "TESTING"
    MAINTAINABILITY = "MAINTAINABILITY"
    CODE_QUALITY = "CODE_QUALITY"
    DOCUMENTATION = "DOCUMENTATION"
    PERFORMANCE = "PERFORMANCE"


class FindingSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    RESOLVED = "RESOLVED"


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "fingerprint",
            name="uq_findings_analysis_fingerprint",
        ),
        Index("ix_findings_analysis_id", "analysis_id"),
        Index("ix_findings_severity", "severity"),
        Index("ix_findings_status", "status"),
        Index("ix_findings_source", "source"),
        Index("ix_findings_category", "category"),
        Index("ix_findings_file_path", "file_path"),
        Index("ix_findings_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("analyses.id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    rule_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    start_line: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    end_line: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    message: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    raw_artifact_uri: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="findings",
    )
