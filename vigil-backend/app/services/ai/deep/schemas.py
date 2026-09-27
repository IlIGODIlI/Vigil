from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.review.schemas import FindingCategory, FindingSeverity, ReviewFinding, ReviewResult, ReviewStatus


class ReviewPlanTarget(BaseModel):
    """Target file and symbol area prioritized for deep code review investigation."""

    model_config = ConfigDict(extra="ignore")

    file: str = Field(..., description="Target file path")
    symbols: List[str] = Field(default_factory=list, description="Target functions/classes in scope")
    areas: List[str] = Field(default_factory=list, description="Review categories to investigate (e.g. security, logic)")
    priority: str = Field(default="medium", description="Priority level: high, medium, low")
    reason: str = Field(..., description="Rationale for targeting this code section")
    evidence: Optional[str] = Field(default=None, description="Diff snippet or metadata justifying target selection")


class ReviewPlan(BaseModel):
    """Structured review plan produced by ReviewPlanner."""

    model_config = ConfigDict(extra="ignore")

    targets: List[ReviewPlanTarget] = Field(default_factory=list, description="Prioritized investigation targets")
    summary: str = Field(default="", description="High-level architectural assessment strategy")
    strategy: str = Field(default="focused", description="Review approach strategy (e.g. security-focused, comprehensive)")


class CandidateFinding(BaseModel):
    """Unverified candidate finding proposed during broad review phase."""

    model_config = ConfigDict(extra="ignore")

    category: FindingCategory = Field(..., description="Hypothesized finding category")
    severity_estimate: FindingSeverity = Field(default=FindingSeverity.MEDIUM, description="Estimated severity")
    title: str = Field(..., description="Short headline hypothesis")
    file: str = Field(..., description="File path under investigation")
    line: Optional[int] = Field(default=None, description="Estimated line number if identifiable")
    problem_hypothesis: str = Field(..., description="Proposed vulnerability or bug hypothesis")
    why_investigate: str = Field(..., description="Rationale explaining why deep evidence check is required")
    evidence: Optional[str] = Field(default=None, description="Initial diff patch snippet supporting hypothesis")
    symbol: Optional[str] = Field(default=None, description="Target symbol name if known")
    priority: str = Field(default="medium", description="Investigation priority: high, medium, low")
    provenance: str = Field(default="broad_review", description="Origin of candidate hypothesis")


class InvestigationEvidence(BaseModel):
    """Structured evidence bundle assembled for candidate investigation."""

    model_config = ConfigDict(extra="ignore")

    candidate: CandidateFinding = Field(..., description="Target candidate finding hypothesis")
    target_symbol: str = Field(default="unavailable", description="Symbol name or 'unavailable'")
    callers: List[str] = Field(default_factory=lambda: ["unavailable"], description="Caller symbols or ['unavailable']")
    callees: List[str] = Field(default_factory=lambda: ["unavailable"], description="Callee symbols or ['unavailable']")
    relevant_tests: List[str] = Field(default_factory=list, description="Associated test file paths")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Related configuration directives")
    scanner_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Corroborating scanner findings")
    git_history: str = Field(default="unavailable", description="Historical commit context or 'unavailable'")
    diff_evidence: Optional[str] = Field(default=None, description="Relevant diff patch snippet")
    repository_evidence: Optional[str] = Field(default=None, description="Broader repository context excerpt")
    provenance: List[str] = Field(default_factory=list, description="Data sources utilized (e.g. diff, test, scanner, unavailable)")


class ReviewMatrixItem(BaseModel):
    """Category-level review matrix evaluation result."""

    model_config = ConfigDict(extra="ignore")

    category: str = Field(..., description="Category name (e.g. Security, Logic)")
    applicable: bool = Field(..., description="Whether category applies to PR context")
    reviewed: bool = Field(..., description="Whether category was evaluated")
    evidence_count: int = Field(default=0, description="Count of findings in category")
    status: str = Field(default="UNAVAILABLE", description="UI status: YES, NO, UNAVAILABLE, N/A")
    reason: Optional[str] = Field(default=None, description="Explanation when not applicable or not reviewed")


class ReviewLimitation(BaseModel):
    """Structured operational limitation of the review execution context."""

    model_config = ConfigDict(extra="ignore")

    limitation: str = Field(..., description="Description of missing context or limitation")
    category: str = Field(..., description="Limitation category")
    impact: str = Field(..., description="Impact on review thoroughness")
    status: str = Field(default="UNAVAILABLE", description="UI status: UNAVAILABLE or NOT_EXECUTED")


class ReviewCoverage(BaseModel):
    """Structured coverage tracking metrics for an AI code review."""

    model_config = ConfigDict(extra="ignore")

    changed_files: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "reviewed": 0},
        description="File review counts: {'total': N, 'reviewed': M}",
    )
    changed_symbols: Optional[Dict[str, int]] = Field(
        default=None,
        description="Symbol review counts: {'total': N, 'reviewed': M} or None if unavailable",
    )
    tests_reviewed: Optional[int] = Field(
        default=None,
        description="Count of tests reviewed or None if unavailable",
    )
    dependencies_reviewed: Optional[int] = Field(
        default=None,
        description="Count of dependency configs reviewed or None if unavailable",
    )
    scanner_findings_reviewed: Optional[int] = Field(
        default=None,
        description="Count of scanner findings reviewed or None if unavailable",
    )
    status_summary: Dict[str, str] = Field(
        default_factory=dict,
        description="UI-facing status mapping (e.g. {'changed_files': 'YES', 'changed_symbols': 'UNAVAILABLE'})",
    )
    changed_files_examined: List[str] = Field(default_factory=list)
    changed_symbols_examined: List[str] = Field(default_factory=list)
    categories_considered: List[str] = Field(default_factory=list)
    categories_skipped: Dict[str, str] = Field(default_factory=dict)
    candidates_generated: int = 0
    candidates_investigated: int = 0
    candidates_dropped: int = 0
    final_findings: int = 0
    execution_status: str = Field(default="SUCCESS", description="Coverage outcome status (SUCCESS, PARTIAL, WARNING)")


class DeepReviewLimits(BaseModel):
    """Configurable budget and bounds for Deep Intelligence Engine execution."""

    model_config = ConfigDict(extra="ignore")

    max_planner_calls: int = 1
    max_candidates: int = 10
    max_investigations: int = 5
    max_context_chars: int = 60_000
    max_total_model_calls: int = 7
