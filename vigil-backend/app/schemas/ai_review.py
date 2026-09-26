from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.context.schemas import (
    ChangedFileContext,
    RepositoryStructureContext,
    ScannerFindingContext,
)
from app.services.ai.review.schemas import ReviewFinding


class AIReviewRequest(BaseModel):
    """Request payload for triggering an AI code review on a pull request."""

    model_config = ConfigDict(extra="ignore")

    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional reviewer focus directives (e.g. 'Focus on security and SQL injection')",
    )
    analysis_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional specific analysis ID to attach review and findings to",
    )
    persist: bool = Field(
        default=False,
        description="Whether to persist the review and findings into the VIGIL database",
    )
    changed_files: Optional[List[ChangedFileContext]] = Field(
        default=None,
        description="Optional explicit changed files with diffs (supplied by upstream GitHub/diff service)",
    )
    scanner_findings: Optional[List[ScannerFindingContext]] = Field(
        default=None,
        description="Optional explicit scanner findings (supplied by upstream static analysis tools)",
    )
    repository_structure: Optional[RepositoryStructureContext] = Field(
        default=None,
        description="Optional repository structure, files, and dependencies context",
    )
    review_depth: str = Field(
        default="standard",
        description="Review execution depth: 'standard' (single pass) or 'deep' (multi-pass Deep Intelligence Engine)",
    )


class AIReviewResponse(BaseModel):
    """Structured response model representing the outcome of an AI pull request review."""

    model_config = ConfigDict(extra="ignore")

    pull_request_id: uuid.UUID = Field(..., description="ID of the pull request reviewed")
    analysis_id: Optional[uuid.UUID] = Field(default=None, description="Associated analysis record ID if available")
    review_id: Optional[uuid.UUID] = Field(default=None, description="Persisted Review entity ID if persist=True")
    status: str = Field(..., description="Review outcome status (SUCCESS, WARNING, MALFORMED_OUTPUT, READY)")
    summary: str = Field(..., description="High-level narrative review summary")
    findings_count: int = Field(default=0, description="Total validated findings produced")
    grounded_findings: int = Field(default=0, description="Count of findings successfully grounded in diff evidence")
    dropped_findings: int = Field(default=0, description="Count of hallucinated findings rejected by validator")
    findings: List[ReviewFinding] = Field(default_factory=list, description="List of validated, grounded findings")
    warnings: List[str] = Field(default_factory=list, description="Parser or validation warnings encountered")
    model: str = Field(..., description="AI model identifier that performed the review")
    review_depth: str = Field(default="standard", description="Review depth executed ('standard' or 'deep')")
    coverage: Optional[Dict[str, Any]] = Field(default=None, description="Structured coverage metrics")
    review_matrix: Optional[List[Dict[str, Any]]] = Field(default=None, description="Structured review matrix per category")
    limitations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Structured review context limitations")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of review generation",
    )
