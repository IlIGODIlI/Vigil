"""Vigil Repository Context & Code Understanding Engine (Member 2)."""

from app.services.repository_context.languages import (
    detect_language,
    is_supported_language,
    SUPPORTED_CODE_LANGUAGES,
)
from app.services.repository_context.metadata import (
    FileMetadata,
    create_file_metadata,
    normalize_repo_path,
    compute_file_sha256,
)
from app.services.repository_context.scanner import (
    RepositoryScanner,
    RepositoryTree,
    DEFAULT_IGNORE_DIRS,
)
from app.services.repository_context.parsers import (
    ParsedClass,
    ParsedFileResult,
    ParsedFunction,
    ParsedImport,
    PythonASTParser,
    TreeSitterParser,
    parse_source_file,
)

from app.services.repository_context.relevance import (
    RelevanceScoreConfig,
    RelevantFileSelector,
    ScoredFile,
)

from app.services.repository_context.git import (
    CommitFileChange,
    CommitInfo,
    GitContext,
    GitContextExtractor,
)

from app.services.repository_context.context_contract import (
    DependencyRelationship,
    RepositoryContext,
    RepositorySummary,
)

from app.services.repository_context.budget import ContextBudget
from app.services.repository_context.llm_context import (
    LLMContextGenerator,
    sanitize_untrusted_text,
)
from app.services.repository_context.engine import RepositoryContextEngine

__all__ = [
    "detect_language",
    "is_supported_language",
    "SUPPORTED_CODE_LANGUAGES",
    "FileMetadata",
    "create_file_metadata",
    "normalize_repo_path",
    "compute_file_sha256",
    "RepositoryScanner",
    "RepositoryTree",
    "DEFAULT_IGNORE_DIRS",
    "ParsedClass",
    "ParsedFileResult",
    "ParsedFunction",
    "ParsedImport",
    "PythonASTParser",
    "TreeSitterParser",
    "parse_source_file",
    "RelevanceScoreConfig",
    "RelevantFileSelector",
    "ScoredFile",
    "CommitFileChange",
    "CommitInfo",
    "GitContext",
    "GitContextExtractor",
    "DependencyRelationship",
    "RepositoryContext",
    "RepositorySummary",
    "ContextBudget",
    "LLMContextGenerator",
    "sanitize_untrusted_text",
    "RepositoryContextEngine",
]




