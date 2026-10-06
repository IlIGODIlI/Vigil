"""Repository filesystem scanner and tree extractor."""

import logging
import os
import re
from typing import Dict, Iterable, List, Optional, Set
from pydantic import BaseModel, Field

from app.services.repository_context.metadata import (
    FileMetadata,
    compute_file_sha256,
    create_file_metadata,
    normalize_repo_path,
)

logger = logging.getLogger(__name__)

# Default directory ignore patterns
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "target",
    "coverage",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".turbo",
    ".gradle",
    ".svn",
    ".hg",
}

# Binary and non-source extensions that should not be parsed as source
DEFAULT_BINARY_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".pyd",
    ".class",
    ".jar",
    ".war",
    ".db",
    ".sqlite",
    ".sqlite3",
}


class RepositoryTree(BaseModel):
    """Structured representation of the scanned repository tree."""

    root_path: str = Field(default="", description="Path of the repository root")
    files: List[FileMetadata] = Field(default_factory=list, description="List of file metadata items")
    total_files: int = Field(default=0, description="Total count of non-ignored files")
    total_size_bytes: int = Field(default=0, description="Total size in bytes across all files")
    languages: Dict[str, int] = Field(
        default_factory=dict, description="Language distribution (language -> count of files)"
    )
    ignored_paths: List[str] = Field(default_factory=list, description="Summary of ignored directories/files")
    errors: List[str] = Field(default_factory=list, description="Non-fatal scan or read errors encountered")

    def get_file(self, rel_path: str) -> Optional[FileMetadata]:
        """Look up metadata for a file by relative path."""
        normalized = normalize_repo_path(rel_path)
        for f in self.files:
            if f.path == normalized:
                return f
        return None

    def get_source_files(self) -> List[FileMetadata]:
        """Return all primary source files."""
        return [f for f in self.files if f.is_source]

    def get_test_files(self) -> List[FileMetadata]:
        """Return all test files."""
        return [f for f in self.files if f.is_test]


class RepositoryScanner:
    """Scanner for extracting structured file trees and metadata from repositories."""

    def __init__(
        self,
        ignore_dirs: Optional[Iterable[str]] = None,
        custom_ignore_patterns: Optional[Iterable[str]] = None,
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10 MB default limit
    ):
        self.ignore_dirs: Set[str] = set(ignore_dirs) if ignore_dirs is not None else set(DEFAULT_IGNORE_DIRS)
        self.custom_patterns: List[re.Pattern] = [
            re.compile(p) for p in (custom_ignore_patterns or [])
        ]
        self.max_file_size_bytes: int = max_file_size_bytes

    def is_ignored_directory(self, dir_name: str) -> bool:
        """Check if a directory name matches the ignore list or custom patterns."""
        if dir_name in self.ignore_dirs:
            return True
        for pattern in self.custom_patterns:
            if pattern.search(dir_name):
                return True
        return False

    def is_ignored_file(self, rel_path: str) -> bool:
        """Check if a file should be ignored during scanning."""
        normalized = normalize_repo_path(rel_path)
        parts = normalized.split("/")

        # Check if any parent directory is an ignored directory
        for part in parts[:-1]:
            if part in self.ignore_dirs:
                return True

        for pattern in self.custom_patterns:
            if pattern.search(normalized):
                return True

        return False

    def scan_directory(
        self,
        root_dir: str,
        compute_hashes: bool = True,
    ) -> RepositoryTree:
        """Recursively scan a local repository directory.

        Resilient to filesystem errors, broken symlinks, and permission issues.
        """
        root_path = os.path.abspath(root_dir)
        if not os.path.exists(root_path):
            return RepositoryTree(
                root_path=root_dir,
                errors=[f"Repository root directory does not exist: {root_dir}"],
            )

        tree = RepositoryTree(root_path=root_path)

        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            # Filter out ignored directories in-place so os.walk does not recurse into them
            original_dirs = list(dirnames)
            dirnames[:] = [
                d
                for d in original_dirs
                if not self.is_ignored_directory(d)
                and not self.is_ignored_file(
                    normalize_repo_path(os.path.relpath(os.path.join(dirpath, d), root_path))
                )
            ]

            # Record ignored directories for auditability
            for ignored in set(original_dirs) - set(dirnames):
                rel_ignored = normalize_repo_path(
                    os.path.relpath(os.path.join(dirpath, ignored), root_path)
                )
                tree.ignored_paths.append(rel_ignored)

            for filename in filenames:
                file_full_path = os.path.join(dirpath, filename)
                try:
                    rel_path = normalize_repo_path(os.path.relpath(file_full_path, root_path))

                    if self.is_ignored_file(rel_path):
                        tree.ignored_paths.append(rel_path)
                        continue

                    # Safe file stat
                    try:
                        stat = os.stat(file_full_path)
                        size_bytes = stat.st_size
                    except (OSError, PermissionError) as e:
                        tree.errors.append(f"Cannot stat file {rel_path}: {str(e)}")
                        size_bytes = 0

                    file_hash: Optional[str] = None
                    if compute_hashes and size_bytes <= self.max_file_size_bytes:
                        file_hash = compute_file_sha256(
                            file_full_path, max_bytes=self.max_file_size_bytes
                        )

                    metadata = create_file_metadata(
                        rel_path=rel_path,
                        size_bytes=size_bytes,
                        file_hash=file_hash,
                    )

                    tree.files.append(metadata)
                    tree.total_files += 1
                    tree.total_size_bytes += size_bytes
                    tree.languages[metadata.language] = (
                        tree.languages.get(metadata.language, 0) + 1
                    )

                except Exception as e:
                    logger.warning("Error processing file %s: %s", file_full_path, e)
                    tree.errors.append(f"Error processing {file_full_path}: {str(e)}")

        return tree

    def scan_from_file_list(
        self,
        files: List[dict],
        root_path: str = "",
    ) -> RepositoryTree:
        """Build a RepositoryTree from a list of file dictionaries (e.g. from GitHub Trees API).

        Expected dict keys:
          - "path": relative path
          - "size": optional size in bytes
          - "sha": optional commit / blob sha
        """
        tree = RepositoryTree(root_path=root_path)

        for item in files:
            path = item.get("path")
            if not path:
                continue

            rel_path = normalize_repo_path(path)
            if self.is_ignored_file(rel_path):
                tree.ignored_paths.append(rel_path)
                continue

            size_bytes = item.get("size", 0)
            file_hash = item.get("sha")

            metadata = create_file_metadata(
                rel_path=rel_path,
                size_bytes=size_bytes,
                file_hash=file_hash,
            )

            tree.files.append(metadata)
            tree.total_files += 1
            tree.total_size_bytes += size_bytes
            tree.languages[metadata.language] = (
                tree.languages.get(metadata.language, 0) + 1
            )

        return tree
