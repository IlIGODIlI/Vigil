from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PullRequestContext(BaseModel):
    """Contextual metadata representing a pull request under review."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Title of the pull request")
    description: Optional[str] = Field(default=None, description="Body description or PR markdown notes")
    author: Optional[str] = Field(default=None, description="GitHub username of the PR author")
    source_branch: Optional[str] = Field(default=None, description="Head/feature branch name")
    target_branch: Optional[str] = Field(default=None, description="Base/target branch name (e.g. main)")
    head_sha: Optional[str] = Field(default=None, description="Latest commit SHA on the PR branch")
    base_sha: Optional[str] = Field(default=None, description="Target branch merge base SHA")
    pr_number: Optional[int] = Field(default=None, description="Pull request number")


class CommitContext(BaseModel):
    """Contextual metadata representing a single commit in the change history."""

    model_config = ConfigDict(extra="ignore")

    sha: str = Field(..., description="Commit SHA hash")
    message: str = Field(..., description="Commit commit message")
    author: Optional[str] = Field(default=None, description="Author username or name")
    committed_at: Optional[datetime] = Field(default=None, description="Commit timestamp")
    parent_sha: Optional[str] = Field(default=None, description="Parent commit SHA")


class ChangedFileContext(BaseModel):
    """Context representing a single modified, added, or deleted file with diff and content."""

    model_config = ConfigDict(extra="ignore")

    file_path: str = Field(..., description="Relative path of the changed file in the repository")
    change_type: Optional[str] = Field(
        default=None,
        description="Change classification: 'added', 'modified', 'deleted', 'renamed'",
    )
    additions: Optional[int] = Field(default=None, description="Number of added lines")
    deletions: Optional[int] = Field(default=None, description="Number of deleted lines")
    diff_patch: Optional[str] = Field(default=None, description="Unified diff patch for this file")
    file_content: Optional[str] = Field(
        default=None,
        description="Full or relevant section of the file content for additional context",
    )
    old_content: Optional[str] = Field(default=None, description="Original file content before changes")
    new_content: Optional[str] = Field(default=None, description="Updated file content after changes")


class RepositoryStructureContext(BaseModel):
    """Context describing repository structure, languages, and dependency declarations."""

    model_config = ConfigDict(extra="ignore")

    repository_name: Optional[str] = Field(default=None, description="Full repository name (e.g. owner/repo)")
    file_paths: List[str] = Field(
        default_factory=list,
        description="Repository file paths or relevant tree structure",
    )
    relevant_directories: List[str] = Field(
        default_factory=list,
        description="High-level directories relevant to this review",
    )
    languages: List[str] = Field(
        default_factory=list,
        description="Primary programming languages identified in the repository",
    )
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Manifest dependencies and versions (e.g. package.json or requirements.txt)",
    )
    test_paths: List[str] = Field(
        default_factory=list,
        description="Paths of relevant unit or integration test files",
    )


class ScannerFindingContext(BaseModel):
    """Context representing an automated scanner finding (Semgrep, Gitleaks, Trivy, etc.)."""

    model_config = ConfigDict(extra="ignore")

    source: str = Field(..., description="Scanner source identifier (e.g., 'SEMGREP', 'GITLEAKS')")
    category: str = Field(..., description="Finding category (e.g., 'SECURITY', 'LOGIC')")
    severity: str = Field(..., description="Severity level (e.g., 'HIGH', 'MEDIUM', 'LOW', 'INFO')")
    rule_id: Optional[str] = Field(default=None, description="Scanner rule or check identifier")
    file_path: Optional[str] = Field(default=None, description="Target file path")
    start_line: Optional[int] = Field(default=None, description="Starting line number")
    end_line: Optional[int] = Field(default=None, description="Ending line number")
    message: str = Field(..., description="Scanner finding description or diagnosis")
    evidence: Optional[Dict[str, Any]] = Field(default=None, description="Raw scanner evidence or snippets")


class ReviewContext(BaseModel):
    """Top-level aggregate context container passed into the review prompt engine."""

    model_config = ConfigDict(extra="ignore")

    pull_request: Optional[PullRequestContext] = Field(
        default=None,
        description="Pull request metadata",
    )
    commits: List[CommitContext] = Field(
        default_factory=list,
        description="List of commits included in this review",
    )
    changed_files: List[ChangedFileContext] = Field(
        default_factory=list,
        description="List of changed files with diffs and contents",
    )
    repository: Optional[RepositoryStructureContext] = Field(
        default=None,
        description="Repository tree and environment structure",
    )
    scanner_findings: List[ScannerFindingContext] = Field(
        default_factory=list,
        description="Automated findings from static analyzers and security scanners",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional reviewer instructions or specific focus areas (e.g. 'Focus on auth')",
    )
