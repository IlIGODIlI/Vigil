from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.commit_analysis import CommitAnalysisOverallStatus


class CommitIntent(str, Enum):
    FEATURE = "FEATURE"
    BUG_FIX = "BUG_FIX"
    REFACTOR = "REFACTOR"
    DOCUMENTATION = "DOCUMENTATION"
    DEPENDENCY_UPDATE = "DEPENDENCY_UPDATE"
    TEST = "TEST"
    FORMATTING = "FORMATTING"
    CONFIGURATION = "CONFIGURATION"
    OTHER = "OTHER"


class CompletenessSignalType(str, Enum):
    TODO_DETECTED = "TODO_DETECTED"
    PLACEHOLDER_DETECTED = "PLACEHOLDER_DETECTED"
    MISSING_TEST_COVERAGE = "MISSING_TEST_COVERAGE"
    NO_OBVIOUS_ERROR_HANDLING = "NO_OBVIOUS_ERROR_HANDLING"
    IMPLEMENTATION_DETECTED = "IMPLEMENTATION_DETECTED"
    DOCUMENTATION_CHANGE_DETECTED = "DOCUMENTATION_CHANGE_DETECTED"
    TEST_CHANGE_DETECTED = "TEST_CHANGE_DETECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CompletenessSignal(BaseModel):
    type: CompletenessSignalType
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: str
    description: str


class CommitAnalysisContext(BaseModel):
    commit_sha: str
    commit_message: str
    changed_files: List[Dict[str, Any]] = Field(default_factory=list)
    diff: str = ""
    repository_context: Optional[Any] = None
    test_context: Optional[Dict[str, Any]] = None
    git_context: Optional[Dict[str, Any]] = None


class CommitAnalysisResult(BaseModel):
    commit_sha: str
    summary: str
    intent: CommitIntent
    implementation_notes: str
    testing_notes: str
    error_handling_notes: str
    documentation_notes: str
    placeholder_notes: str
    completeness_signals: List[CompletenessSignal] = Field(default_factory=list)
    overall_status: CommitAnalysisOverallStatus
