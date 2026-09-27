import re
from typing import Any, Dict, List, Optional
from app.services.commit_analysis.schemas import CommitIntent

# Standard dependency files
DEPENDENCY_FILES = {
    "requirements.txt",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pyproject.toml",
    "cargo.toml",
    "go.mod",
    "go.sum",
}

# Configuration files
CONFIG_EXTENSIONS = {".ini", ".yaml", ".yml", ".toml", ".json", ".conf", ".cfg"}
CONFIG_FILES = {"alembic.ini", "dockerfile", "docker-compose.yml", ".gitignore", ".env.example"}


def classify_commit_intent(
    message: str,
    changed_files: List[Dict[str, Any]],
    diff: str = "",
) -> CommitIntent:
    """
    Classifies the intent of a commit deterministically using commit message,
    changed file paths, and diff characteristics.
    """
    clean_msg = (message or "").strip().lower()
    file_paths = [
        f.get("filename", "").lower() for f in changed_files if isinstance(f, dict) and f.get("filename")
    ]

    # Rule 1: File-path based strict classification (when all changed files share a specific type)
    if file_paths:
        is_all_dep = all(
            any(fp.endswith(dep_f) or fp == dep_f for dep_f in DEPENDENCY_FILES)
            for fp in file_paths
        )
        if is_all_dep:
            return CommitIntent.DEPENDENCY_UPDATE

        is_all_doc = all(
            (fp.endswith((".md", ".rst")) or fp == "readme.txt" or fp.startswith("docs/") or fp == "readme" or "readme." in fp)
            and not any(fp.endswith(dep_f) or fp == dep_f for dep_f in DEPENDENCY_FILES)
            for fp in file_paths
        )
        if is_all_doc:
            return CommitIntent.DOCUMENTATION

        is_all_test = all(
            fp.startswith("tests/") or fp.startswith("test/") or "test_" in fp or "_test." in fp
            for fp in file_paths
        )
        if is_all_test:
            return CommitIntent.TEST

        is_all_config = all(
            any(fp.endswith(ext) for ext in CONFIG_EXTENSIONS) or fp in CONFIG_FILES
            for fp in file_paths
        )
        if is_all_config and not any(kw in clean_msg for kw in ["feat", "fix", "add"]):
            return CommitIntent.CONFIGURATION

    # Rule 2: Message keyword/prefix matching
    if re.search(r"^(build|chore|deps?|dependency)(\([^\)]+\))?:", clean_msg) or "bump " in clean_msg or "upgrade " in clean_msg or "dependency" in clean_msg:
        return CommitIntent.DEPENDENCY_UPDATE

    if re.search(r"^(docs?|documentation)(\([^\)]+\))?:", clean_msg) or "update readme" in clean_msg or "docs:" in clean_msg:
        return CommitIntent.DOCUMENTATION

    if re.search(r"^(test|tests)(\([^\)]+\))?:", clean_msg) or "add tests" in clean_msg or "unit test" in clean_msg:
        return CommitIntent.TEST

    if re.search(r"^(style|format|formatting)(\([^\)]+\))?:", clean_msg) or "format code" in clean_msg or "reformat" in clean_msg or "lint" in clean_msg:
        return CommitIntent.FORMATTING

    if re.search(r"^(refactor)(\([^\)]+\))?:", clean_msg) or "refactor " in clean_msg or "clean up" in clean_msg or "cleanup" in clean_msg:
        return CommitIntent.REFACTOR

    if re.search(r"^(fix|bugfix|hotfix)(\([^\)]+\))?:", clean_msg) or "fix " in clean_msg or "bug" in clean_msg or "issue " in clean_msg or "resolve" in clean_msg:
        return CommitIntent.BUG_FIX

    if re.search(r"^(feat|feature)(\([^\)]+\))?:", clean_msg) or "add " in clean_msg or "implement" in clean_msg or "new " in clean_msg or "create " in clean_msg:
        return CommitIntent.FEATURE

    # Rule 3: Check diff characteristics if available
    if diff and ("only whitespace" in diff.lower() or diff.strip() == ""):
        return CommitIntent.FORMATTING

    # Fallback: Allow OTHER/UNKNOWN rather than forcing an incorrect classification
    return CommitIntent.OTHER
