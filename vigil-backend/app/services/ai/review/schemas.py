from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FindingCategory(str, Enum):
    """Standardized finding categories for AI-generated code reviews."""

    SECURITY = "Security"
    LOGIC = "Logic"
    ERROR_HANDLING = "Error Handling"
    TESTING = "Testing"
    MAINTAINABILITY = "Maintainability"
    CODE_QUALITY = "Code Quality"
    DOCUMENTATION = "Documentation"
    PERFORMANCE = "Performance"


class FindingSeverity(str, Enum):
    """Standardized severity levels for AI-generated review findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    """Review processing and validation status."""

    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    PARTIAL = "PARTIAL"


class ReviewFinding(BaseModel):
    """Structured finding proposed by the AI code review engine."""

    model_config = ConfigDict(extra="ignore")

    category: FindingCategory = Field(
        ...,
        description="Finding category (e.g. Security, Logic, Error Handling)",
    )
    severity: FindingSeverity = Field(
        ...,
        description="Severity level (info, low, medium, high, critical)",
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Short, descriptive headline summarizing the finding",
    )
    file: str = Field(
        ...,
        min_length=1,
        description="Relative file path where the issue occurs",
    )
    line: Optional[int] = Field(
        default=None,
        ge=1,
        description="Target line number (1-indexed) in the file if identifiable",
    )
    problem: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the bug, vulnerability, or design flaw",
    )
    why: str = Field(
        ...,
        min_length=1,
        description="Explanation of the risk, impact, or failure mode if unaddressed",
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Quoted code snippet or observed pattern from the diff verifying the issue",
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Concrete recommended remediation or code fix",
    )
    source: str = Field(
        default="AI",
        description="Finding originator (defaults to 'AI')",
    )
    is_grounded: bool = Field(
        default=True,
        description="Whether the file and evidence have been verified against the review context",
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            cleaned = v.strip().replace("_", " ").title()
            for cat in FindingCategory:
                if cat.value.lower() == cleaned.lower():
                    return cat
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            cleaned = v.strip().lower()
            for sev in FindingSeverity:
                if sev.value.lower() == cleaned:
                    return sev
        return v


class ReviewResult(BaseModel):
    """Validated structured code review output returned by ReviewEngine."""

    model_config = ConfigDict(extra="ignore")

    summary: str = Field(
        ...,
        description="Executive summary of the pull request changes and review assessment",
    )
    findings: List[ReviewFinding] = Field(
        default_factory=list,
        description="List of verified, evidence-grounded findings",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model identifier that produced the completion",
    )
    status: ReviewStatus = Field(
        default=ReviewStatus.SUCCESS,
        description="Overall review parsing and validation outcome",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation notes, hallucination alerts, or parsing fallback notices",
    )
    validation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Operational metrics (e.g. grounded_count, dropped_hallucinations, parse_method)",
    )
    raw_response: Optional[str] = Field(
        default=None,
        description="Original raw text response produced by the model",
    )
