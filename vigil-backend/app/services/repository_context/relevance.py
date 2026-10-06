"""Deterministic relevant-file selection for repository context (Member 2 Phase 8).

Note:
    The scoring weights and priority heuristics in this module are pragmatic defaults
    designed to yield deterministic, explainable context selection for AI review.
    They are configurable and are not claimed to be scientifically optimal.
"""

import os
from typing import Dict, Iterable, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.services.repository_context.metadata import FileMetadata, normalize_repo_path
from app.services.repository_context.parsers.models import ParsedFileResult


class RelevanceScoreConfig(BaseModel):
    """Configurable scoring weights and caps for relevant-file selection."""

    # High priority weights
    changed_file_weight: float = Field(default=100.0, description="Score for directly changed files")
    direct_import_weight: float = Field(default=50.0, description="Score for files directly imported or importing changed files")
    directly_related_test_weight: float = Field(default=45.0, description="Score for directly corresponding test files")
    inheritance_relationship_weight: float = Field(default=40.0, description="Score for base classes or derived classes")
    direct_referenced_module_weight: float = Field(default=35.0, description="Score for directly referenced local modules")

    # Medium priority weights
    transitive_dependency_weight: float = Field(default=20.0, description="Score for depth-2 transitive imports")
    nearby_module_weight: float = Field(default=15.0, description="Score for files in the same directory/module")
    configuration_weight: float = Field(default=10.0, description="Score for key project configuration files")
    relevant_git_history_weight: float = Field(default=10.0, description="Score for files modified together in recent Git commits")

    # Low priority weights
    unrelated_file_weight: float = Field(default=1.0, description="Base score for remaining non-relevant files")

    # Caps
    max_relevant_files: int = Field(default=20, ge=1, description="Maximum number of relevant files to select")


class ScoredFile(BaseModel):
    """A repository file evaluated with deterministic relevance scoring."""

    path: str = Field(description="Normalized repository-relative file path")
    score: float = Field(default=0.0, description="Total relevance score computed")
    priority: str = Field(default="low", description="Priority tier: 'high', 'medium', or 'low'")
    reasons: List[str] = Field(default_factory=list, description="List of reasons for this file's score")
    is_changed: bool = Field(default=False, description="Whether this file is one of the changed files")


class RelevantFileSelector:
    """Selects and prioritizes repository files relevant to a given set of changed files."""

    def __init__(self, config: Optional[RelevanceScoreConfig] = None):
        self.config = config or RelevanceScoreConfig()

    @staticmethod
    def _get_file_stem(path: str) -> str:
        """Extract the filename stem without extension or common test prefixes/suffixes."""
        base = path.rsplit("/", 1)[-1].lower()
        # Remove extension
        stem = base.rsplit(".", 1)[0] if "." in base else base
        # Strip test markers
        if stem.startswith("test_"):
            stem = stem[5:]
        elif stem.endswith("_test"):
            stem = stem[:-5]
        elif stem.endswith(".test") or stem.endswith(".spec"):
            stem = stem.rsplit(".", 1)[0]
        elif stem.endswith("tests") or stem.endswith("test"):
            stem = stem.rstrip("s")[:-4] if stem.endswith("tests") else stem[:-4]
        return stem

    @classmethod
    def is_directly_related_test(cls, file_a: str, file_b: str) -> bool:
        """Check if file_a and file_b have a direct code-to-test or test-to-code relationship."""
        norm_a = normalize_repo_path(file_a)
        norm_b = normalize_repo_path(file_b)
        if norm_a == norm_b:
            return False

        stem_a = cls._get_file_stem(norm_a)
        stem_b = cls._get_file_stem(norm_b)

        if not stem_a or not stem_b or stem_a != stem_b:
            return False

        # One should be a test path or have test in name, and the other should typically be source
        is_a_test = "test" in norm_a.lower() or "spec" in norm_a.lower()
        is_b_test = "test" in norm_b.lower() or "spec" in norm_b.lower()
        return is_a_test != is_b_test or (is_a_test and is_b_test)

    @staticmethod
    def _resolve_local_import_target(
        source_file: str,
        imported_module: str,
        all_file_paths: Set[str],
    ) -> Optional[str]:
        """Attempt to resolve a local import string (e.g. './auth.js', '../utils', 'app.db') to a repo path."""
        source_dir = source_file.rsplit("/", 1)[0] if "/" in source_file else ""

        # Relative import syntax: ./foo or ../foo
        if imported_module.startswith("."):
            joined = os.path.normpath(os.path.join(source_dir, imported_module)).replace("\\", "/")
            joined = normalize_repo_path(joined)

            # Check direct match
            if joined in all_file_paths:
                return joined
            # Check with common extensions
            for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
                if f"{joined}{ext}" in all_file_paths:
                    return f"{joined}{ext}"
                if f"{joined}/index{ext}" in all_file_paths:
                    return f"{joined}/index{ext}"
            return None

        # Dot-separated Python module syntax: app.services.foo
        dot_as_path = imported_module.replace(".", "/")
        for candidate in all_file_paths:
            candidate_no_ext = candidate.rsplit(".", 1)[0] if "." in candidate else candidate
            if candidate_no_ext == dot_as_path or candidate_no_ext.endswith(f"/{dot_as_path}"):
                return candidate
            if candidate_no_ext.endswith(f"/{dot_as_path}/__init__"):
                return candidate

        return None

    def select_relevant_files(
        self,
        all_files: Iterable[FileMetadata],
        changed_files: Iterable[str],
        parsed_files: Optional[Dict[str, ParsedFileResult]] = None,
        git_co_changed_files: Optional[Dict[str, Set[str]]] = None,
    ) -> List[ScoredFile]:
        """Deterministically score and rank all files in the repository.

        Args:
            all_files: List or collection of FileMetadata for repository files.
            changed_files: List of file paths changed in the current PR or commit.
            parsed_files: Optional mapping from path to ParsedFileResult from code parsers.
            git_co_changed_files: Optional mapping from changed file path to set of files that
                                  historically co-changed with it in recent Git commits.

        Returns:
            List of ScoredFile objects sorted deterministically by score descending, then path ascending.
            Capped at config.max_relevant_files.
        """
        all_files_map: Dict[str, FileMetadata] = {
            normalize_repo_path(f.path): f for f in all_files
        }
        all_paths: Set[str] = set(all_files_map.keys())
        normalized_changed: Set[str] = {
            normalize_repo_path(p) for p in changed_files if normalize_repo_path(p)
        }
        parsed = parsed_files or {}

        # 1. Build import & inheritance graphs
        # direct_imports[A] = set of files B that A imports
        direct_imports: Dict[str, Set[str]] = {p: set() for p in all_paths}
        imported_by: Dict[str, Set[str]] = {p: set() for p in all_paths}
        local_referenced_modules: Dict[str, Set[str]] = {p: set() for p in all_paths}

        # class_to_file[ClassName] = file_path
        class_to_file: Dict[str, str] = {}
        # file_to_classes[file_path] = list of ParsedClass
        file_to_classes: Dict[str, List] = {p: [] for p in all_paths}

        for path, p_res in parsed.items():
            norm_p = normalize_repo_path(path)
            if norm_p not in all_paths:
                continue

            for cls_obj in p_res.classes:
                class_to_file[cls_obj.name] = norm_p
                file_to_classes[norm_p].append(cls_obj)

            for imp in p_res.imports:
                target = self._resolve_local_import_target(norm_p, imp.imported_module, all_paths)
                if target and target in all_paths and target != norm_p:
                    direct_imports[norm_p].add(target)
                    imported_by[target].add(norm_p)
                    if imp.import_type == "local" or imp.imported_module.startswith("."):
                        local_referenced_modules[norm_p].add(target)

        # 2. Build inheritance relationships
        # inheritance_related[file] = set of other files related by inheritance
        inheritance_related: Dict[str, Set[str]] = {p: set() for p in all_paths}
        for file_p, classes in file_to_classes.items():
            for cls_obj in classes:
                for base_name in cls_obj.bases:
                    base_file = class_to_file.get(base_name)
                    if base_file and base_file != file_p:
                        inheritance_related[file_p].add(base_file)
                        inheritance_related[base_file].add(file_p)

        # 3. Transitive dependencies (depth 2 from changed files)
        depth1_imports: Set[str] = set()
        for ch in normalized_changed:
            depth1_imports.update(direct_imports.get(ch, set()))
            depth1_imports.update(imported_by.get(ch, set()))

        transitive_imports: Set[str] = set()
        for d1 in depth1_imports:
            for d2 in direct_imports.get(d1, set()):
                if d2 not in normalized_changed and d2 not in depth1_imports:
                    transitive_imports.add(d2)
            for d2 in imported_by.get(d1, set()):
                if d2 not in normalized_changed and d2 not in depth1_imports:
                    transitive_imports.add(d2)

        # 4. Changed files directories for nearby modules
        changed_dirs: Set[str] = {
            ch.rsplit("/", 1)[0] if "/" in ch else "" for ch in normalized_changed
        }

        # 5. Score each file
        scored_files: List[ScoredFile] = []
        git_history = git_co_changed_files or {}

        for path, meta in all_files_map.items():
            score = 0.0
            reasons: List[str] = []
            is_changed = path in normalized_changed

            # High Priority: Changed file
            if is_changed:
                score += self.config.changed_file_weight
                reasons.append("changed_file")

            # High Priority: Direct imports (imports changed file or is imported by changed file)
            imported_by_changed = any(path in direct_imports.get(ch, set()) for ch in normalized_changed)
            imports_changed = any(ch in direct_imports.get(path, set()) for ch in normalized_changed)
            if imported_by_changed or imports_changed:
                score += self.config.direct_import_weight
                if imported_by_changed:
                    reasons.append("imported_by_changed_file")
                if imports_changed:
                    reasons.append("imports_changed_file")

            # High Priority: Directly related test
            is_related_test = any(self.is_directly_related_test(path, ch) for ch in normalized_changed)
            if is_related_test:
                score += self.config.directly_related_test_weight
                reasons.append("directly_related_test")

            # High Priority: Inheritance relationship
            has_inheritance = any(path in inheritance_related.get(ch, set()) for ch in normalized_changed)
            if has_inheritance:
                score += self.config.inheritance_relationship_weight
                reasons.append("inheritance_relationship")

            # High Priority: Directly referenced local module
            is_local_ref = any(path in local_referenced_modules.get(ch, set()) for ch in normalized_changed) or any(ch in local_referenced_modules.get(path, set()) for ch in normalized_changed)
            if is_local_ref:
                score += self.config.direct_referenced_module_weight
                reasons.append("direct_referenced_local_module")

            # Medium Priority: Transitive dependency
            if path in transitive_imports and not is_changed and not (imported_by_changed or imports_changed):
                score += self.config.transitive_dependency_weight
                reasons.append("transitive_dependency")

            # Medium Priority: Nearby module (same directory)
            file_dir = path.rsplit("/", 1)[0] if "/" in path else ""
            if file_dir in changed_dirs and not is_changed and not is_related_test:
                score += self.config.nearby_module_weight
                reasons.append("nearby_module")

            # Medium Priority: Configuration file
            if meta.is_config and not is_changed:
                score += self.config.configuration_weight
                reasons.append("configuration")

            # Medium Priority: Relevant Git co-change history
            is_git_related = False
            for ch in normalized_changed:
                if path in git_history.get(ch, set()) and not is_changed:
                    is_git_related = True
                    break
            if is_git_related:
                score += self.config.relevant_git_history_weight
                reasons.append("relevant_git_history")

            # Low Priority: Base score if no specific reasons found
            if not reasons:
                score += self.config.unrelated_file_weight
                reasons.append("unrelated_file")

            # Determine priority tier
            if score >= 35.0:
                priority = "high"
            elif score >= 10.0:
                priority = "medium"
            else:
                priority = "low"

            scored_files.append(
                ScoredFile(
                    path=path,
                    score=score,
                    priority=priority,
                    reasons=reasons,
                    is_changed=is_changed,
                )
            )

        # Deterministic sort: score DESC, path ASC
        scored_files.sort(key=lambda sf: (-sf.score, sf.path))

        # Apply maximum limit
        return scored_files[: self.config.max_relevant_files]
