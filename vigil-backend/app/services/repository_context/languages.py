"""Language detection and language capability registry for repository context understanding."""

from typing import Dict, Optional, Set

# Extension to language name mapping (lowercase extension with dot)
EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    # Core supported languages
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    # Common repository languages
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".swift": "swift",
    ".dockerfile": "dockerfile",
    ".env": "properties",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
}

# Special filenames to language mapping
FILENAME_TO_LANGUAGE: Dict[str, str] = {
    "dockerfile": "dockerfile",
    "containerfile": "dockerfile",
    "makefile": "makefile",
    "jenkinsfile": "groovy",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "vagrantfile": "ruby",
}

# Languages with active parsing / symbol extraction support
SUPPORTED_CODE_LANGUAGES: Set[str] = {
    "python",
    "javascript",
    "typescript",
    "java",
}


def detect_language(filename: str) -> str:
    """Detect the programming or markup language for a given filename.

    Returns the canonical lowercase language identifier, or 'unknown' if not recognized.
    Never raises an exception on malformed or unusual filenames.
    """
    if not filename:
        return "unknown"

    clean_name = filename.strip().lower()

    # Check whole filename first (e.g., Dockerfile)
    base_name = clean_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if base_name in FILENAME_TO_LANGUAGE:
        return FILENAME_TO_LANGUAGE[base_name]

    # Check extension
    if "." in base_name:
        ext = "." + base_name.rsplit(".", 1)[-1]
        return EXTENSION_TO_LANGUAGE.get(ext, "unknown")

    return "unknown"


def is_supported_language(language: str) -> bool:
    """Check if the language has active AST/Tree-sitter code understanding support."""
    return language.lower() in SUPPORTED_CODE_LANGUAGES
