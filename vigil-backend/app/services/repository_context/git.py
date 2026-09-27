"""Read-only Git history and commit context extractor (Member 2 Phase 9).

Note:
    This module performs strictly read-only repository inspection using GitPython.
    It never pushes, mutates, or authenticates with remote GitHub instances.
"""

import logging
import os
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.services.repository_context.metadata import normalize_repo_path

logger = logging.getLogger(__name__)

try:
    import git
    from git.exc import GitError, InvalidGitRepositoryError, NoSuchPathError
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False


class CommitFileChange(BaseModel):
    """File-level change details within a specific commit."""

    path: str = Field(description="Normalized relative path of the file")
    change_type: str = Field(default="modified", description="'added', 'modified', 'deleted', 'renamed'")
    additions: int = Field(default=0, ge=0, description="Lines inserted")
    deletions: int = Field(default=0, ge=0, description="Lines deleted")


class CommitInfo(BaseModel):
    """Comprehensive structured metadata for a single Git commit."""

    sha: str = Field(description="Full or abbreviated commit SHA hash")
    author: str = Field(description="Name of the commit author")
    author_email: Optional[str] = Field(default=None, description="Email of the author")
    timestamp: str = Field(description="ISO 8601 formatted commit timestamp")
    message: str = Field(description="Commit commit message subject and body")
    changed_files: List[CommitFileChange] = Field(default_factory=list, description="List of file changes in this commit")
    additions: int = Field(default=0, ge=0, description="Total line additions across this commit")
    deletions: int = Field(default=0, ge=0, description="Total line deletions across this commit")

    def get_file_paths(self) -> List[str]:
        """Return list of paths changed in this commit."""
        return [f.path for f in self.changed_files]


class GitContext(BaseModel):
    """Aggregated read-only Git history and commit context for repository analysis."""

    current_branch: Optional[str] = Field(default=None, description="Active Git branch name if available")
    head_sha: Optional[str] = Field(default=None, description="Current HEAD commit SHA")
    recent_commits: List[CommitInfo] = Field(default_factory=list, description="Ordered recent commit history (newest first)")
    file_history: Dict[str, List[CommitInfo]] = Field(
        default_factory=dict, description="Commit history filtered for specific changed files"
    )
    is_git_repo: bool = Field(default=True, description="Whether the root path is a valid Git repository")
    errors: List[str] = Field(default_factory=list, description="Non-fatal Git extraction error messages")

    def get_co_changed_files(self, changed_files: List[str]) -> Dict[str, Set[str]]:
        """Return mapping of changed_file -> set of other files that co-changed in recent commits."""
        normalized_targets = {normalize_repo_path(f) for f in changed_files}
        co_changed: Dict[str, Set[str]] = {target: set() for target in normalized_targets}

        for commit in self.recent_commits:
            commit_paths = {normalize_repo_path(c.path) for c in commit.changed_files}
            intersect = commit_paths.intersection(normalized_targets)
            if intersect:
                for target in intersect:
                    co_changed[target].update(commit_paths - {target})

        return co_changed


class GitContextExtractor:
    """Safely extracts read-only Git history and commit metadata."""

    @staticmethod
    def _find_git_root(start_path: str) -> Optional[str]:
        """Find the enclosing .git directory by walking up from start_path."""
        curr = os.path.abspath(start_path)
        while True:
            if os.path.exists(os.path.join(curr, ".git")):
                return curr
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
        return None

    def extract_git_context(
        self,
        repo_path: str,
        max_commits: int = 20,
        changed_files: Optional[List[str]] = None,
    ) -> GitContext:
        """Extract recent commit history and per-file context from a local repository.

        Args:
            repo_path: Directory path to inspect.
            max_commits: Maximum number of recent repository commits to collect.
            changed_files: Optional list of files to collect specific per-file history for.

        Returns:
            Populated GitContext object. Safe against missing Git, uninitialized repos, or errors.
        """
        if not GITPYTHON_AVAILABLE:
            return GitContext(
                is_git_repo=False,
                errors=["GitPython is not installed in the environment."],
            )

        git_root = self._find_git_root(repo_path)
        if not git_root:
            return GitContext(
                is_git_repo=False,
                errors=[f"Directory is not part of a Git repository: {repo_path}"],
            )

        repo = None
        try:
            repo = git.Repo(git_root)

            # Check if repo has any commits
            try:
                head_commit = repo.head.commit
                head_sha = head_commit.hexsha
            except (ValueError, GitError, AttributeError):
                # Repository is empty / unborn HEAD
                return GitContext(
                    is_git_repo=True,
                    current_branch=None,
                    head_sha=None,
                    recent_commits=[],
                    errors=["Repository has no commits or HEAD is unborn."],
                )

            current_branch: Optional[str] = None
            try:
                if not repo.head.is_detached:
                    current_branch = repo.active_branch.name
            except Exception:
                current_branch = None

            git_ctx = GitContext(
                current_branch=current_branch,
                head_sha=head_sha,
                is_git_repo=True,
            )

            def build_commit_info(c: git.Commit) -> CommitInfo:
                files_changed: List[CommitFileChange] = []
                additions = 0
                deletions = 0

                try:
                    stats = c.stats
                    additions = stats.total.get("insertions", 0)
                    deletions = stats.total.get("deletions", 0)

                    for f_path, f_stats in stats.files.items():
                        norm_p = normalize_repo_path(f_path)
                        files_changed.append(
                            CommitFileChange(
                                path=norm_p,
                                change_type="modified",
                                additions=f_stats.get("insertions", 0),
                                deletions=f_stats.get("deletions", 0),
                            )
                        )
                except Exception as stat_err:
                    logger.debug("Could not compute detailed commit stats for %s: %s", c.hexsha, stat_err)

                # Detect change types (added, deleted, modified) if parent exists
                if c.parents and files_changed:
                    try:
                        diffs = c.parents[0].diff(c)
                        change_map: Dict[str, str] = {}
                        for d in diffs:
                            p = normalize_repo_path(d.b_path or d.a_path or "")
                            if d.new_file:
                                change_map[p] = "added"
                            elif d.deleted_file:
                                change_map[p] = "deleted"
                            elif d.renamed_file:
                                change_map[p] = "renamed"
                            else:
                                change_map[p] = "modified"

                        for fc in files_changed:
                            if fc.path in change_map:
                                fc.change_type = change_map[fc.path]
                    except Exception:
                        pass

                return CommitInfo(
                    sha=c.hexsha,
                    author=c.author.name or "Unknown",
                    author_email=c.author.email,
                    timestamp=c.committed_datetime.isoformat(),
                    message=c.message.strip(),
                    changed_files=files_changed,
                    additions=additions,
                    deletions=deletions,
                )

            # 1. Collect recent repository commits
            try:
                commits = list(repo.iter_commits(max_count=max_commits))
                git_ctx.recent_commits = [build_commit_info(c) for c in commits]
            except Exception as e:
                git_ctx.errors.append(f"Error iterating repository commits: {str(e)}")

            # 2. Collect per-file history for changed files
            if changed_files:
                # Calculate prefix difference if repo_path is a subdirectory of git_root
                rel_prefix = normalize_repo_path(os.path.relpath(repo_path, git_root))
                if rel_prefix == ".":
                    rel_prefix = ""

                for file_path in changed_files:
                    norm_p = normalize_repo_path(file_path)
                    git_query_path = f"{rel_prefix}/{norm_p}".strip("/") if rel_prefix else norm_p

                    try:
                        f_commits = list(repo.iter_commits(paths=git_query_path, max_count=10))
                        if f_commits:
                            git_ctx.file_history[norm_p] = [build_commit_info(c) for c in f_commits]
                    except Exception as file_err:
                        git_ctx.errors.append(f"Error fetching history for {norm_p}: {str(file_err)}")

            return git_ctx

        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            return GitContext(
                is_git_repo=False,
                errors=[f"Cannot open Git repository at {git_root}: {str(e)}"],
            )
        except Exception as e:
            return GitContext(
                is_git_repo=False,
                errors=[f"Unexpected error opening Git repository: {str(e)}"],
            )
        finally:
            if repo is not None:
                try:
                    repo.close()
                except Exception:
                    pass
