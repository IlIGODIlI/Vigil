from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.ai.context.normalizer import ContextNormalizer, ContextSizeLimits
from app.services.ai.context.schemas import (
    ChangedFileContext,
    CommitContext,
    PullRequestContext,
    RepositoryStructureContext,
    ReviewContext,
    ScannerFindingContext,
)


class ReviewContextBuilder:
    """Fluent builder for constructing, aggregating, and normalizing ReviewContext instances."""

    def __init__(self, normalizer: Optional[ContextNormalizer] = None):
        self._pull_request: Optional[PullRequestContext] = None
        self._commits: List[CommitContext] = []
        self._changed_files: List[ChangedFileContext] = []
        self._repository: Optional[RepositoryStructureContext] = None
        self._scanner_findings: List[ScannerFindingContext] = []
        self._custom_instructions: Optional[str] = None
        self._normalizer = normalizer or ContextNormalizer()

    def set_pull_request(
        self,
        title: str,
        description: Optional[str] = None,
        author: Optional[str] = None,
        source_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        head_sha: Optional[str] = None,
        base_sha: Optional[str] = None,
        pr_number: Optional[int] = None,
    ) -> "ReviewContextBuilder":
        self._pull_request = PullRequestContext(
            title=title,
            description=description,
            author=author,
            source_branch=source_branch,
            target_branch=target_branch,
            head_sha=head_sha,
            base_sha=base_sha,
            pr_number=pr_number,
        )
        return self

    def add_commit(
        self,
        sha: str,
        message: str,
        author: Optional[str] = None,
        committed_at: Optional[datetime] = None,
        parent_sha: Optional[str] = None,
    ) -> "ReviewContextBuilder":
        self._commits.append(
            CommitContext(
                sha=sha,
                message=message,
                author=author,
                committed_at=committed_at,
                parent_sha=parent_sha,
            )
        )
        return self

    def add_changed_file(
        self,
        file_path: str,
        diff_patch: Optional[str] = None,
        change_type: Optional[str] = None,
        additions: Optional[int] = None,
        deletions: Optional[int] = None,
        file_content: Optional[str] = None,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ) -> "ReviewContextBuilder":
        self._changed_files.append(
            ChangedFileContext(
                file_path=file_path,
                diff_patch=diff_patch,
                change_type=change_type,
                additions=additions,
                deletions=deletions,
                file_content=file_content,
                old_content=old_content,
                new_content=new_content,
            )
        )
        return self

    def set_repository(
        self,
        repository_name: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        relevant_directories: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        dependencies: Optional[Dict[str, str]] = None,
        test_paths: Optional[List[str]] = None,
    ) -> "ReviewContextBuilder":
        self._repository = RepositoryStructureContext(
            repository_name=repository_name,
            file_paths=file_paths or [],
            relevant_directories=relevant_directories or [],
            languages=languages or [],
            dependencies=dependencies or {},
            test_paths=test_paths or [],
        )
        return self

    def add_scanner_finding(
        self,
        source: str,
        category: str,
        severity: str,
        message: str,
        rule_id: Optional[str] = None,
        file_path: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> "ReviewContextBuilder":
        self._scanner_findings.append(
            ScannerFindingContext(
                source=source,
                category=category,
                severity=severity,
                rule_id=rule_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                message=message,
                evidence=evidence,
            )
        )
        return self

    def set_custom_instructions(self, instructions: Optional[str]) -> "ReviewContextBuilder":
        self._custom_instructions = instructions
        return self

    def build(self, normalize: bool = True) -> ReviewContext:
        """Constructs the ReviewContext instance and applies normalization if requested."""
        raw_context = ReviewContext(
            pull_request=self._pull_request,
            commits=self._commits,
            changed_files=self._changed_files,
            repository=self._repository,
            scanner_findings=self._scanner_findings,
            custom_instructions=self._custom_instructions,
        )

        if normalize:
            return self._normalizer.normalize(raw_context)
        return raw_context
