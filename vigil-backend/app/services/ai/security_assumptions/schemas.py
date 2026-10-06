from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.review.schemas import FindingConfidence, FindingSeverity


class AssumptionScope(str, Enum):
    """Scope/domain where a security or behavioral assumption applies."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT = "input"
    VALIDATION = "validation"
    ENDPOINT = "endpoint"
    STATE = "state"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    TRUST_BOUNDARY = "trust_boundary"


class AssumptionChangeType(str, Enum):
    """Type of transition observed for a security assumption in a pull request."""

    INTRODUCED = "INTRODUCED"
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"
    CONTRADICTED = "CONTRADICTED"


class SecurityAssumption(BaseModel):
    """Structured internal representation of a discovered security or behavioral assumption."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Unique or descriptive identifier for the assumption")
    scope: AssumptionScope = Field(..., description="Domain/scope of the assumption")
    target: str = Field(..., description="Function name, route path, model field, or entity being governed")
    expected_value: Any = Field(..., description="Assumed requirement, type, constraint, or condition")
    source_file: str = Field(..., description="File path where assumption was extracted")
    source_line: Optional[int] = Field(default=None, description="Line number of assumption definition")
    confidence: FindingConfidence = Field(default=FindingConfidence.HIGH, description="Confidence rating")
    evidence: str = Field(..., description="Exact code or syntax demonstrating the assumption")
    description: Optional[str] = Field(default=None, description="Human-readable summary of the assumption")


class SecurityAssumptionDetectionResult(BaseModel):
    """Result of comparing before/after security assumptions."""

    model_config = ConfigDict(extra="ignore")

    detected: bool = False
    severity: FindingSeverity = FindingSeverity.MEDIUM
    confidence: FindingConfidence = FindingConfidence.HIGH
    title: str = ""
    file_path: str = ""
    line_number: Optional[int] = None
    assumption_name: str = ""
    scope: str = ""
    previous_assumption: str = ""
    new_assumption: str = ""
    change_type: AssumptionChangeType = AssumptionChangeType.CHANGED
    potential_repercussions: str = ""
    problem: str = ""
    why: str = ""
    evidence: Optional[str] = None
    suggestion: str = ""
