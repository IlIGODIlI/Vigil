"""Unified code parser dispatcher routing files to Python AST or Tree-sitter parsers."""

import logging
from typing import Optional, Set

from app.services.repository_context.languages import detect_language, is_supported_language
from app.services.repository_context.parsers.models import (
    ParsedClass,
    ParsedFileResult,
    ParsedFunction,
    ParsedImport,
)
from app.services.repository_context.parsers.python_parser import PythonASTParser
from app.services.repository_context.parsers.treesitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)

# Singleton instance of Tree-sitter parser
_tree_sitter_parser: Optional[TreeSitterParser] = None


def get_treesitter_parser() -> TreeSitterParser:
    global _tree_sitter_parser
    if _tree_sitter_parser is None:
        _tree_sitter_parser = TreeSitterParser()
    return _tree_sitter_parser


def parse_source_file(
    file_path: str,
    content: str,
    language: Optional[str] = None,
    local_packages: Optional[Set[str]] = None,
) -> ParsedFileResult:
    """Parse a source code file into structured functions, classes, imports, and calls.

    Resilient to syntax errors, unsupported languages, and malformed files.
    """
    detected_lang = language or detect_language(file_path)

    if not is_supported_language(detected_lang):
        return ParsedFileResult(
            file_path=file_path,
            language=detected_lang,
            functions=[],
            classes=[],
            imports=[],
            calls=[],
            parse_error=f"Language '{detected_lang}' is not currently configured for AST parsing",
        )

    try:
        if detected_lang == "python":
            return PythonASTParser.parse(
                file_path=file_path,
                content=content,
                local_packages=local_packages,
            )
        elif detected_lang in {"javascript", "typescript", "java"}:
            parser = get_treesitter_parser()
            return parser.parse(
                file_path=file_path,
                content=content,
                language=detected_lang,
            )
        else:
            return ParsedFileResult(
                file_path=file_path,
                language=detected_lang,
                parse_error=f"No parser available for {detected_lang}",
            )
    except Exception as e:
        logger.warning("Unexpected parser error for file %s: %s", file_path, e)
        return ParsedFileResult(
            file_path=file_path,
            language=detected_lang,
            parse_error=f"Failed to parse source: {str(e)}",
        )
