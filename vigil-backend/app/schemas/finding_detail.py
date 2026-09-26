"""
Phase 6 — Extended finding schemas.

Extends the existing FindingRead with:
- FindingDetail: rich detail view for reviewer inspection
- VerifyFindingRequest: human verification action payload
- FindingQueueItem: lightweight queue entry (no giant context blobs)
- FindingQueueListResponse: paginated queue
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.base import PaginatedResponse
from app.schemas.finding_verification import FindingVerificationRead


# ─── Verification request ────────────────────────────────────────────────────

VALID_DECISIONS = {"VERIFIED", "REJECTED", "DISMISSED"}


class VerifyFindingRequest(BaseModel):
    """
    Payload for a human reviewer's verification action.

    decision must be one of: VERIFIED, REJECTED, DISMISSED.
    comment is optional but strongly encouraged.
    """
    decision: str = Field(
        ...,
        description="Reviewer decision: VERIFIED, REJECTED, or DISMISSED",
    )
    comment: Optional[str] = Field(
        None,
        max_length=4000,
        description="Optional reviewer comment or justification",
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        upper = v.upper()
        if upper not in VALID_DECISIONS:
            raise ValueError(
                f"Invalid decision '{v}'. Must be one of: {', '.join(sorted(VALID_DECISIONS))}"
            )
        return upper


# ─── Finding detail (rich view for reviewer) ─────────────────────────────────

class AnalysisSummary(BaseModel):
    """Lightweight analysis context for the finding detail view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    head_sha: str
    status: str
    trigger_type: str
    created_at: datetime


class RepositorySummary(BaseModel):
    """Lightweight repository context for the finding detail view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    owner_login: str
    name: str
    html_url: str


class PullRequestSummary(BaseModel):
    """Lightweight PR context for the finding detail view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pr_number: int
    title: str
    head_sha: str
    source_branch: str
    target_branch: str
    status: str


class FindingDetail(BaseModel):
    """
    Rich finding representation for the reviewer detail endpoint.

    Provides all information a reviewer needs to understand, evaluate,
    and verify a finding without exposing the full repository context.

    The evidence field contains the AI reasoning and specific code
    evidence extracted from the commit diff.  The original AI-generated
    evidence is READ-ONLY — it cannot be mutated through this endpoint.
    """
    model_config = ConfigDict(from_attributes=True)

    # Core finding identity
    id: uuid.UUID
    analysis_id: uuid.UUID
    source: str
    category: str
    severity: str
    rule_id: Optional[str] = None
    fingerprint: str

    # Code location
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    # Human-readable content
    message: str

    # Verification lifecycle
    status: str

    # AI evidence — immutable after creation
    evidence: Optional[Dict[str, Any]] = None

    created_at: datetime

    # Verification history (append-only audit)
    verification_history: List[FindingVerificationRead] = Field(default_factory=list)

    # Surrounding context (injected by service, not a DB field)
    analysis: Optional[AnalysisSummary] = None
    pull_request: Optional[PullRequestSummary] = None
    repository: Optional[RepositorySummary] = None


# ─── Review queue ─────────────────────────────────────────────────────────────

class FindingQueueItem(BaseModel):
    """
    Lightweight queue entry.

    Only the fields a reviewer needs to triage without the heavy
    evidence payload.  Evidence is fetched via GET /findings/{id}.
    """
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    analysis_id: uuid.UUID
    repository_full_name: Optional[str] = None
    repository_id: Optional[uuid.UUID] = None
    pull_request_id: Optional[uuid.UUID] = None
    pull_request_number: Optional[int] = None
    commit_sha: Optional[str] = None
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    severity: str
    category: str
    source: str
    # Short title extracted from message (first line)
    title: str
    status: str
    created_at: datetime


class FindingQueueListResponse(PaginatedResponse):
    items: List[FindingQueueItem]
