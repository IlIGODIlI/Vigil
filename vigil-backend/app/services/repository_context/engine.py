"""Unified Repository Context Engine and integration interfaces (Member 2 Phase 14).

This engine serves as the single entry point coordinating:
- Filesystem scanning & tree extraction
- Safe multi-language AST & Tree-sitter parsing
- Deterministic relevant-file selection
- Read-only Git history & commit context
- Pydantic output contract packaging
- LLM prompt generation with prompt-injection defenses

Security Notice:
    All repository analysis in this engine is strictly static and read-only.
    Source files, build scripts, tests, and configuration files are never executed.
"""

import logging
import os
from typing import Dict, List, Optional, Set

from app.services.repository_context.budget import ContextBudget
from app.services.repository_context.context_contract import (
    DependencyRelationship,
    RepositoryContext,
    RepositorySummary,
)
from app.services.repository_context.git import GitContext, GitContextExtractor
from app.services.repository_context.llm_context import LLMContextGenerator
from app.services.repository_context.metadata import FileMetadata, normalize_repo_path
from app.services.repository_context.parsers.dispatcher import parse_source_file
from app.services.repository_context.parsers.models import (
    ParsedClass,
    ParsedFileResult,
    ParsedFunction,
    ParsedImport,
)
from app.services.repository_context.relevance import (
    RelevanceScoreConfig,
    RelevantFileSelector,
    ScoredFile,
)
from app.services.repository_context.scanner import RepositoryScanner, RepositoryTree

logger = logging.getLogger(__name__)


class RepositoryContextEngine:
    """Core coordinator for Member 2 code understanding and repository context."""

    def __init__(
        self,
        scanner: Optional[RepositoryScanner] = None,
        git_extractor: Optional[GitContextExtractor] = None,
    ):
        self.scanner = scanner or RepositoryScanner()
        self.git_extractor = git_extractor or GitContextExtractor()

    def build_repository_context(
        self,
        repo_path: str,
        changed_files: Optional[List[str]] = None,
        relevance_config: Optional[RelevanceScoreConfig] = None,
        max_commits: int = 20,
        max_files_to_parse: int = 150,
    ) -> RepositoryContext:
        """Analyze a repository and build a complete, serializable RepositoryContext.

        Args:
            repo_path: Path to the local repository root.
            changed_files: List of file paths modified in the pull request or commit.
            relevance_config: Configurable weights and limits for file relevance.
            max_commits: Maximum number of recent Git commits to collect.
            max_files_to_parse: Safety cap on number of source files to parse with AST/Tree-sitter.

        Returns:
            Fully populated RepositoryContext model.
        """
        abs_repo_path = os.path.abspath(repo_path)
        repo_name = os.path.basename(abs_repo_path)
        normalized_changed = [normalize_repo_path(f) for f in (changed_files or []) if f]

        # 1. Scan filesystem hierarchy
        tree = self.scanner.scan_directory(abs_repo_path)

        # 2. Extract read-only Git history
        git_ctx = self.git_extractor.extract_git_context(
            abs_repo_path,
            max_commits=max_commits,
            changed_files=normalized_changed,
        )

        # 3. Parse source files safely
        # Prioritize changed files, test files, and source code files
        parsed_results: Dict[str, ParsedFileResult] = {}
        files_to_parse: List[FileMetadata] = []

        changed_set = set(normalized_changed)
        # First priority: changed files
        for f in tree.files:
            if f.path in changed_set and (f.is_source or f.is_test):
                files_to_parse.append(f)

        # Second priority: remaining source and test files
        for f in tree.files:
            if f.path not in changed_set and (f.is_source or f.is_test):
                if len(files_to_parse) < max_files_to_parse:
                    files_to_parse.append(f)

        for meta in files_to_parse:
            file_abs_path = os.path.join(abs_repo_path, meta.path)
            try:
                # Read file safely with binary/encoding fallback
                if not os.path.isfile(file_abs_path) or meta.size_bytes > 5 * 1024 * 1024:
                    continue

                with open(file_abs_path, "r", encoding="utf-8", errors="replace") as sf:
                    code_content = sf.read()

                parsed_res = parse_source_file(
                    file_path=meta.path,
                    content=code_content,
                    language=meta.language,
                )
                parsed_results[meta.path] = parsed_res

            except Exception as e:
                logger.debug("Non-fatal error reading/parsing %s: %s", meta.path, e)
                parsed_results[meta.path] = ParsedFileResult(
                    file_path=meta.path,
                    language=meta.language,
                    parse_error=f"Read error: {str(e)}",
                )

        # 4. Relevant-file selection (Phase 8)
        co_changed = git_ctx.get_co_changed_files(normalized_changed) if git_ctx else None
        selector = RelevantFileSelector(config=relevance_config)
        relevant_files = selector.select_relevant_files(
            all_files=tree.files,
            changed_files=normalized_changed,
            parsed_files=parsed_results,
            git_co_changed_files=co_changed,
        )

        # 5. Build cross-file dependency relationships
        dependencies = self._build_dependency_relationships(parsed_results, tree.files)

        # 6. Aggregate functions, classes, imports across relevant and changed files
        functions: List[ParsedFunction] = []
        classes: List[ParsedClass] = []
        imports: List[ParsedImport] = []

        relevant_paths = {rf.path for rf in relevant_files} | set(normalized_changed)
        for path in sorted(relevant_paths):
            res = parsed_results.get(path)
            if res:
                functions.extend(res.functions)
                classes.extend(res.classes)
                imports.extend(res.imports)

        # 7. Identify test suite files
        test_files = tree.get_test_files()

        # 8. Repository summary
        top_languages = sorted(tree.languages.keys(), key=lambda l: tree.languages[l], reverse=True)[:5]
        repo_summary = RepositorySummary(
            name=repo_name,
            root_path=abs_repo_path,
            default_branch=git_ctx.current_branch,
            primary_languages=top_languages,
            total_files=tree.total_files,
            total_size_bytes=tree.total_size_bytes,
        )

        return RepositoryContext(
            repository=repo_summary,
            tree=tree,
            changed_files=normalized_changed,
            relevant_files=relevant_files,
            functions=functions,
            classes=classes,
            imports=imports,
            dependencies=dependencies,
            tests=test_files,
            git_history=git_ctx.recent_commits,
            commit_context=git_ctx,
        )

    def _build_dependency_relationships(
        self,
        parsed_results: Dict[str, ParsedFileResult],
        all_files: List[FileMetadata],
    ) -> List[DependencyRelationship]:
        """Derive explicit cross-file dependency graph relationships."""
        deps: List[DependencyRelationship] = []
        all_paths = {normalize_repo_path(f.path) for f in all_files}

        # Class lookup
        class_to_file: Dict[str, str] = {}
        for path, p_res in parsed_results.items():
            for c in p_res.classes:
                class_to_file[c.name] = path

        for path, p_res in parsed_results.items():
            # 1. Imports
            for imp in p_res.imports:
                target = RelevantFileSelector._resolve_local_import_target(path, imp.imported_module, all_paths)
                if target:
                    deps.append(
                        DependencyRelationship(
                            source_file=path,
                            target=target,
                            relation_type="import",
                            details=f"imports {', '.join(imp.symbols) if imp.symbols else imp.imported_module}",
                        )
                    )
                else:
                    deps.append(
                        DependencyRelationship(
                            source_file=path,
                            target=imp.imported_module,
                            relation_type="import",
                            details=f"external/stdlib import ({imp.import_type})",
                        )
                    )

            # 2. Inheritance
            for c in p_res.classes:
                for base in c.bases:
                    target_file = class_to_file.get(base)
                    if target_file and target_file != path:
                        deps.append(
                            DependencyRelationship(
                                source_file=path,
                                target=target_file,
                                relation_type="inherits",
                                details=f"{c.name} extends {base}",
                            )
                        )

            # 3. Test-of relationships
            for other_meta in all_files:
                if other_meta.is_source and RelevantFileSelector.is_directly_related_test(path, other_meta.path):
                    deps.append(
                        DependencyRelationship(
                            source_file=path,
                            target=other_meta.path,
                            relation_type="test_of",
                            details=f"Test file for {other_meta.name}",
                        )
                    )

        return deps

    # -------------------------------------------------------------------------
    # Member Integration Interfaces (Phase 14)
    # -------------------------------------------------------------------------
    def build_context_from_pr_payload(
        self,
        repo_path: str,
        changed_files: List[str],
        repo_name: Optional[str] = None,
        default_branch: Optional[str] = None,
        relevance_config: Optional[RelevanceScoreConfig] = None,
    ) -> RepositoryContext:
        """Integration interface for Member 1 (PR / Webhook / Ingestion service)."""
        ctx = self.build_repository_context(
            repo_path=repo_path,
            changed_files=changed_files,
            relevance_config=relevance_config,
        )
        if repo_name:
            ctx.repository.name = repo_name
        if default_branch:
            ctx.repository.default_branch = default_branch
        return ctx

    def generate_llm_context(
        self,
        context: RepositoryContext,
        budget: Optional[ContextBudget] = None,
    ) -> str:
        """Integration interface for Member 3 (AI Code Review Engine)."""
        generator = LLMContextGenerator(budget=budget)
        return generator.generate(context)

    def get_commit_context(
        self,
        repo_path: str,
        changed_files: Optional[List[str]] = None,
        max_commits: int = 20,
    ) -> GitContext:
        """Integration interface for Member 4 (Risk & Policy Engine)."""
        return self.git_extractor.extract_git_context(
            repo_path=repo_path,
            max_commits=max_commits,
            changed_files=changed_files,
        )

    @staticmethod
    def serialize_context_for_persistence(context: RepositoryContext) -> dict:
        """Integration interface for Member 5 (Context Persistence Engine)."""
        return context.to_dict()
