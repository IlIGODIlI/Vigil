"""
Phase 6 — Finding Verification model.

Records every human verification decision on a Finding.
This table is append-only from the application's perspective — decisions
are never deleted or overwritten; new rows are added for each action,
providing a full audit trail.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding


class FindingVerification(Base):
    """
    Audit record of a human reviewer's decision on a Finding.

    Invariants:
    - One row per reviewer action. Never updated, only appended.
    - The most recent row for a finding_id represents the current state.
    - reviewer_login is captured at the time of the decision and is
      not a FK so that audit records survive user record changes.
    """
    __tablename__ = "finding_verifications"
    __table_args__ = (
        Index("ix_fv_finding_id", "finding_id"),
        Index("ix_fv_reviewer_login", "reviewer_login"),
        Index("ix_fv_decision", "decision"),
        Index("ix_fv_decided_at", "decided_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("findings.id"),
        nullable=False,
    )
    # Store reviewer identity as a string snapshot — survives user record changes.
    reviewer_login: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Reviewer Vigil user ID at time of decision (optional FK for traceability).
    reviewer_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    # State the finding was in BEFORE this decision (for audit clarity).
    previous_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    finding: Mapped["Finding"] = relationship(
        "Finding",
        back_populates="verifications",
    )
