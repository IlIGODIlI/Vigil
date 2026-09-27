"""Structured Pydantic output contract for Repository Context (Member 2 Phase 10).

This contract defines the authoritative output model consumed by:
- Member 3 (AI Code Review Engine)
- Member 4 (Risk & Policy Engine)
- Member 5 (Context Persistence Engine)
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.repository_context.git import CommitInfo, GitContext
from app.services.repository_context.metadata import FileMetadata
from app.services.repository_context.parsers.models import (
    ParsedClass,
    ParsedFunction,
    ParsedImport,
)
from app.services.repository_context.relevance import ScoredFile
from app.services.repository_context.scanner import RepositoryTree


class RepositorySummary(BaseModel):
    """High-level summary of the repository."""

    name: str = Field(default="", description="Repository name or directory basename")
    root_path: str = Field(default="", description="Absolute or normalized path of the repository root")
    default_branch: Optional[str] = Field(default=None, description="Primary or active branch name")
    primary_languages: List[str] = Field(default_factory=list, description="Top detected programming languages")
    total_files: int = Field(default=0, ge=0, description="Total count of repository files scanned")
    total_size_bytes: int = Field(default=0, ge=0, description="Total byte size of all scanned files")


class DependencyRelationship(BaseModel):
    """A directed dependency relationship between repository entities."""

    source_file: str = Field(description="Normalized path of the origin file")
    target: str = Field(description="Target file, module, or symbol being depended upon")
    relation_type: str = Field(
        description="Type of dependency: 'import', 'inherits', 'calls', or 'test_of'"
    )
    details: Optional[str] = Field(default=None, description="Optional extra metadata or symbol context")


class RepositoryContext(BaseModel):
    """Complete, self-contained, serializable repository context output contract."""

    repository: RepositorySummary = Field(description="Repository metadata and summary statistics")
    tree: RepositoryTree = Field(description="Scanned file tree hierarchy and per-file metadata")
    changed_files: List[str] = Field(default_factory=list, description="List of files changed in current PR/commit")
    relevant_files: List[ScoredFile] = Field(default_factory=list, description="Ranked and scored relevant files")
    functions: List[ParsedFunction] = Field(default_factory=list, description="Extracted functions and methods across relevant files")
    classes: List[ParsedClass] = Field(default_factory=list, description="Extracted classes and data structures across relevant files")
    imports: List[ParsedImport] = Field(default_factory=list, description="Extracted imports across relevant files")
    dependencies: List[DependencyRelationship] = Field(default_factory=list, description="Explicit cross-file dependency graph edges")
    tests: List[FileMetadata] = Field(default_factory=list, description="Identified test suite files")
    git_history: List[CommitInfo] = Field(default_factory=list, description="Recent commit history")
    commit_context: Optional[GitContext] = Field(default=None, description="Detailed Git branch and per-file commit history")

    def to_dict(self) -> dict:
        """Serialize repository context to a JSON-compatible Python dictionary."""
        return self.model_dump()

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize repository context to a JSON string."""
        return self.model_dump_json(indent=indent)
