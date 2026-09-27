import re
from typing import List, Optional

from app.services.ai.context.schemas import (
    ChangedFileContext,
    CommitContext,
    PullRequestContext,
    RepositoryStructureContext,
    ReviewContext,
    ScannerFindingContext,
)


class ContextSizeLimits:
    """Configurable sizing and truncation constraints for assembling review contexts."""

    def __init__(
        self,
        max_total_diff_chars: int = 60_000,
        max_file_diff_chars: int = 15_000,
        max_file_content_chars: int = 10_000,
        max_files: int = 30,
        max_commits: int = 20,
        max_findings: int = 50,
        max_tree_paths: int = 100,
        max_text_field_chars: int = 4_000,
    ):
        self.max_total_diff_chars = max_total_diff_chars
        self.max_file_diff_chars = max_file_diff_chars
        self.max_file_content_chars = max_file_content_chars
        self.max_files = max_files
        self.max_commits = max_commits
        self.max_findings = max_findings
        self.max_tree_paths = max_tree_paths
        self.max_text_field_chars = max_text_field_chars


class ContextNormalizer:
    """Sanitizes, normalizes, and bounds review context data to protect trust boundaries and context windows."""

    def __init__(self, limits: Optional[ContextSizeLimits] = None):
        self.limits = limits or ContextSizeLimits()

    @staticmethod
    def sanitize_untrusted_text(text: Optional[str], max_len: Optional[int] = None) -> Optional[str]:
        """Sanitizes untrusted text by removing null bytes, normalizing control characters,

        and safely neutralising structural breakout tokens.
        """
        if text is None:
            return None

        # Remove null bytes and carriage returns
        cleaned = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")

        # Neutralize XML closing tags that could attempt to break out of data delimiters
        # e.g., </pull_request>, </diff>, </untrusted_code>, etc.
        cleaned = re.sub(
            r"</(untrusted_[a-zA-Z0-9_]+|pull_request|commit|diff|finding|file|repo)[^>]*>",
            r"&lt;/\1&gt;",
            cleaned,
            flags=re.IGNORECASE,
        )

        if max_len is not None and len(cleaned) > max_len:
            cleaned = cleaned[:max_len] + f"\n... [TRUNCATED: Exceeded {max_len} character limit] ..."

        return cleaned.strip()

    @staticmethod
    def normalize_path(path: Optional[str]) -> Optional[str]:
        """Normalizes file paths into clean relative POSIX paths."""
        if not path:
            return None
        cleaned = path.replace("\\", "/").strip()
        # Remove leading slashes and dot-slashes
        cleaned = re.sub(r"^(\./|/)+", "", cleaned)
        # Prevent traversal
        cleaned = cleaned.replace("../", "")
        return cleaned

    def normalize(self, context: ReviewContext) -> ReviewContext:
        """Applies normalization, sanitization, and truncation budget to a ReviewContext."""
        # 1. Normalize Pull Request
        norm_pr = None
        if context.pull_request:
            norm_pr = PullRequestContext(
                title=self.sanitize_untrusted_text(context.pull_request.title, max_len=500) or "Untitled PR",
                description=self.sanitize_untrusted_text(
                    context.pull_request.description, max_len=self.limits.max_text_field_chars
                ),
                author=self.sanitize_untrusted_text(context.pull_request.author, max_len=100),
                source_branch=self.sanitize_untrusted_text(context.pull_request.source_branch, max_len=200),
                target_branch=self.sanitize_untrusted_text(context.pull_request.target_branch, max_len=200),
                head_sha=self.sanitize_untrusted_text(context.pull_request.head_sha, max_len=64),
                base_sha=self.sanitize_untrusted_text(context.pull_request.base_sha, max_len=64),
                pr_number=context.pull_request.pr_number,
            )

        # 2. Normalize Commits (bounded by max_commits)
        norm_commits: List[CommitContext] = []
        for c in context.commits[: self.limits.max_commits]:
            norm_commits.append(
                CommitContext(
                    sha=c.sha[:64],
                    message=self.sanitize_untrusted_text(c.message, max_len=self.limits.max_text_field_chars) or "",
                    author=self.sanitize_untrusted_text(c.author, max_len=100),
                    committed_at=c.committed_at,
                    parent_sha=c.parent_sha[:64] if c.parent_sha else None,
                )
            )

        # 3. Normalize Changed Files (with individual and cumulative diff truncation)
        norm_files: List[ChangedFileContext] = []
        accumulated_diff_chars = 0

        for f in context.changed_files[: self.limits.max_files]:
            norm_path = self.normalize_path(f.file_path) or "unknown_file"

            # Truncate individual diff
            diff_patch = f.diff_patch
            if diff_patch:
                if len(diff_patch) > self.limits.max_file_diff_chars:
                    diff_patch = (
                        diff_patch[: self.limits.max_file_diff_chars]
                        + f"\n... [TRUNCATED: File diff exceeded limit of {self.limits.max_file_diff_chars} characters] ..."
                    )

                # Check cumulative budget
                if accumulated_diff_chars + len(diff_patch) > self.limits.max_total_diff_chars:
                    remaining_budget = max(0, self.limits.max_total_diff_chars - accumulated_diff_chars)
                    if remaining_budget > 200:
                        diff_patch = (
                            diff_patch[:remaining_budget]
                            + "\n... [TRUNCATED: Cumulative diff budget exceeded] ..."
                        )
                    else:
                        diff_patch = "[TRUNCATED: Omitted due to cumulative diff budget limit]"
                    accumulated_diff_chars = self.limits.max_total_diff_chars
                else:
                    accumulated_diff_chars += len(diff_patch)

            # Truncate content if present
            file_content = None
            if f.file_content:
                file_content = self.sanitize_untrusted_text(
                    f.file_content, max_len=self.limits.max_file_content_chars
                )

            norm_files.append(
                ChangedFileContext(
                    file_path=norm_path,
                    change_type=f.change_type,
                    additions=f.additions,
                    deletions=f.deletions,
                    diff_patch=self.sanitize_untrusted_text(diff_patch),
                    file_content=file_content,
                )
            )

        # 4. Normalize Repository Structure
        norm_repo = None
        if context.repository:
            norm_repo = RepositoryStructureContext(
                repository_name=self.sanitize_untrusted_text(context.repository.repository_name, max_len=200),
                file_paths=[
                    self.normalize_path(p) or p
                    for p in context.repository.file_paths[: self.limits.max_tree_paths]
                ],
                relevant_directories=[
                    self.normalize_path(d) or d
                    for d in context.repository.relevant_directories[:20]
                ],
                languages=context.repository.languages[:10],
                dependencies=dict(list(context.repository.dependencies.items())[:50]),
                test_paths=[
                    self.normalize_path(p) or p
                    for p in context.repository.test_paths[:30]
                ],
            )

        # 5. Normalize Scanner Findings
        norm_findings: List[ScannerFindingContext] = []
        for sf in context.scanner_findings[: self.limits.max_findings]:
            norm_findings.append(
                ScannerFindingContext(
                    source=self.sanitize_untrusted_text(sf.source, max_len=50) or "UNKNOWN",
                    category=self.sanitize_untrusted_text(sf.category, max_len=50) or "GENERAL",
                    severity=self.sanitize_untrusted_text(sf.severity, max_len=20) or "INFO",
                    rule_id=self.sanitize_untrusted_text(sf.rule_id, max_len=100),
                    file_path=self.normalize_path(sf.file_path),
                    start_line=sf.start_line,
                    end_line=sf.end_line,
                    message=self.sanitize_untrusted_text(sf.message, max_len=1000) or "",
                    evidence=sf.evidence,
                )
            )

        return ReviewContext(
            pull_request=norm_pr,
            commits=norm_commits,
            changed_files=norm_files,
            repository=norm_repo,
            scanner_findings=norm_findings,
            custom_instructions=self.sanitize_untrusted_text(context.custom_instructions, max_len=1000),
        )
