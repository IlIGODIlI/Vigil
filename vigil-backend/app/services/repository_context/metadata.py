"""Structured file metadata models and categorization rules for repository understanding."""

import hashlib
import os
import re
from typing import Optional, Set
from pydantic import BaseModel, Field

from app.services.repository_context.languages import detect_language, is_supported_language


# Known config filenames (case-insensitive)
CONFIG_FILENAMES: Set[str] = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "pipfile",
    "pipfile.lock",
    "poetry.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "tsconfig.json",
    "jsconfig.json",
    "webpack.config.js",
    "vite.config.js",
    "vite.config.ts",
    "rollup.config.js",
    "babel.config.js",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.yml",
    ".prettierrc",
    "pytest.ini",
    "alembic.ini",
    ".env.example",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
}

# Config file extensions
CONFIG_EXTENSIONS: Set[str] = {
    ".ini",
    ".cfg",
    ".conf",
    ".toml",
    ".yaml",
    ".yml",
    ".properties",
}

# Documentation extensions
DOC_EXTENSIONS: Set[str] = {
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".adoc",
    ".pdf",
}

# Documentation filenames (without extension or full filename)
DOC_BASENAMES: Set[str] = {
    "readme",
    "contributing",
    "license",
    "changelog",
    "architecture",
    "code_of_conduct",
    "security",
}

# Test filename patterns
TEST_PATH_REGEX = re.compile(
    r"(^|/|\\)(tests?|__tests__|it|e2e|specs?)(/|\\)|"
    r"(^|/|\\)(test_[^/\\]+|[^/\\]+_test)\.py$|"
    r"(^|/|\\)[^/\\]+\.(test|spec)\.(js|jsx|ts|tsx)$|"
    r"(^|/|\\)[^/\\]+Tests?\.java$",
    re.IGNORECASE,
)

# Generated or minified file patterns
GENERATED_REGEX = re.compile(
    r"\.min\.(js|css)$|"
    r"\.bundle\.(js|css)$|"
    r"\.map$|"
    r"package-lock\.json$|"
    r"yarn\.lock$|"
    r"pnpm-lock\.yaml$|"
    r"poetry\.lock$|"
    r"composer\.lock$",
    re.IGNORECASE,
)


class FileMetadata(BaseModel):
    """Pydantic model representing comprehensive file metadata."""

    path: str = Field(description="Normalized repository-relative path (using forward slashes)")
    name: str = Field(description="File base name including extension")
    extension: str = Field(description="Lowercase file extension including leading dot, or empty")
    language: str = Field(description="Detected language identifier or 'unknown'")
    size_bytes: int = Field(default=0, ge=0, description="File size in bytes")
    is_test: bool = Field(default=False, description="Whether the file represents tests")
    is_source: bool = Field(default=False, description="Whether the file is primary source code")
    is_config: bool = Field(default=False, description="Whether the file is configuration")
    is_documentation: bool = Field(default=False, description="Whether the file is documentation")
    is_generated: bool = Field(default=False, description="Whether the file is generated/bundled/lockfile")
    hash: Optional[str] = Field(default=None, description="SHA-256 checksum of file contents")


def normalize_repo_path(path: str) -> str:
    """Normalize a relative path using forward slashes and strip leading slashes."""
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def determine_file_classification(
    normalized_path: str,
    language: str,
) -> tuple[bool, bool, bool, bool, bool]:
    """Determine the classification flags for a file.

    Returns:
        (is_test, is_source, is_config, is_documentation, is_generated)
    """
    base_name = normalized_path.rsplit("/", 1)[-1].lower()
    name_without_ext = base_name.rsplit(".", 1)[0] if "." in base_name else base_name
    ext = ("." + base_name.rsplit(".", 1)[-1]) if "." in base_name else ""

    # 1. Test detection
    is_test = bool(TEST_PATH_REGEX.search(normalized_path))

    # 2. Generated detection
    is_generated = bool(GENERATED_REGEX.search(base_name))

    # 3. Documentation detection
    is_doc = False
    if name_without_ext in DOC_BASENAMES:
        is_doc = True
    elif ext in DOC_EXTENSIONS:
        is_doc = True
    elif "/docs/" in f"/{normalized_path}/" or "/doc/" in f"/{normalized_path}/":
        is_doc = True

    # 4. Configuration detection
    is_config = False
    if base_name in CONFIG_FILENAMES:
        is_config = True
    elif ext in CONFIG_EXTENSIONS:
        is_config = True
    elif (
        normalized_path.startswith(".github/")
        or normalized_path.startswith(".circleci/")
        or normalized_path.startswith(".gitlab/")
    ):
        is_config = True

    # 5. Source code detection
    # A file is source code if it is in a supported/recognized programming language,
    # and is not purely a config, doc, or generated artifact (unless it is a test,
    # in which case is_test=True, and is_source can still be False or True; we set is_source=True
    # for executable code files that are NOT generated and NOT docs).
    is_code_lang = is_supported_language(language) or language in {
        "go",
        "rust",
        "c",
        "cpp",
        "csharp",
        "ruby",
        "php",
        "kotlin",
        "scala",
        "swift",
        "shell",
    }
    is_source = is_code_lang and not is_config and not is_doc and not is_generated and not is_test

    return is_test, is_source, is_config, is_doc, is_generated


def compute_file_sha256(file_path: str, max_bytes: int = 25 * 1024 * 1024) -> Optional[str]:
    """Compute SHA-256 hash of a file safely.

    Returns hex digest string, or None if file cannot be read or exceeds max_bytes.
    """
    if not os.path.isfile(file_path):
        return None

    try:
        if os.path.getsize(file_path) > max_bytes:
            return None

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (OSError, IOError, PermissionError):
        return None


def compute_content_sha256(content: bytes) -> str:
    """Compute SHA-256 hash of byte content."""
    return hashlib.sha256(content).hexdigest()


def create_file_metadata(
    rel_path: str,
    size_bytes: int = 0,
    file_hash: Optional[str] = None,
) -> FileMetadata:
    """Build a complete FileMetadata model given a relative path."""
    normalized = normalize_repo_path(rel_path)
    base_name = normalized.rsplit("/", 1)[-1]
    ext = ("." + base_name.rsplit(".", 1)[-1].lower()) if "." in base_name else ""
    language = detect_language(normalized)

    is_test, is_source, is_config, is_doc, is_generated = determine_file_classification(
        normalized, language
    )

    return FileMetadata(
        path=normalized,
        name=base_name,
        extension=ext,
        language=language,
        size_bytes=size_bytes,
        is_test=is_test,
        is_source=is_source,
        is_config=is_config,
        is_documentation=is_doc,
        is_generated=is_generated,
        hash=file_hash,
    )
