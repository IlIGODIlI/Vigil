"""
Phase 6 — Schemas for FindingVerification (audit records).
"""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class FindingVerificationRead(BaseModel):
    """Read schema for a single verification decision (audit entry)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    reviewer_login: str
    reviewer_user_id: Optional[str] = None
    decision: str
    comment: Optional[str] = None
    previous_status: str
    decided_at: datetime


class FindingVerificationList(BaseModel):
    """Ordered list of verification history entries for a finding."""
    items: List[FindingVerificationRead]
    total: int
