import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.commit_analysis.schemas import (
    CompletenessSignal,
    CompletenessSignalType,
    CommitAnalysisContext,
)

# Regex patterns for TODO / FIXME
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)

# Risky operations needing error handling
RISKY_OPS = [
    (re.compile(r"\b(open|read_text|write_text|os\.remove|shutil\.)\b"), "file operation"),
    (re.compile(r"\b(httpx\.|requests\.|aiohttp\.|urllib|fetch\()\b"), "network / HTTP call"),
    (re.compile(r"\b(db\.execute|db\.query|session\.execute|session\.commit|db\.commit)\b"), "database operation"),
]


def parse_patch_additions(patch: str) -> List[Tuple[int, str]]:
    """
    Parses a git patch string and returns a list of (line_number, added_line_content)
    tuples corresponding to lines added (+).
    """
    added_lines: List[Tuple[int, str]] = []
    if not patch:
        return added_lines

    current_line = 0
    for line in patch.splitlines():
        if line.startswith("@@"):
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1)) - 1
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            added_lines.append((current_line, line[1:]))
        elif not line.startswith("-"):
            current_line += 1

    return added_lines


class DeterministicAnalyzer:
    """Performs deterministic completeness analysis on commit context."""

    def analyze(self, context: CommitAnalysisContext) -> List[CompletenessSignal]:
        signals: List[CompletenessSignal] = []

        for file_obj in context.changed_files:
            if not isinstance(file_obj, dict):
                continue
            filename = file_obj.get("filename", "")
            patch = file_obj.get("patch", "")

            if not filename or not patch:
                continue

            added_lines = parse_patch_additions(patch)

            # 1. TODO / FIXME Detection
            self._check_todos(filename, added_lines, signals)

            # 2. Placeholder Detection
            self._check_placeholders(filename, added_lines, patch, signals)

            # 3. Error-handling Signals
            self._check_error_handling(filename, added_lines, patch, signals)

        # 4. Test Detection
        self._check_tests(context, signals)

        # 5. Documentation Detection
        self._check_documentation(context, signals)

        return signals

    def _check_todos(
        self,
        filename: str,
        added_lines: List[Tuple[int, str]],
        signals: List[CompletenessSignal],
    ) -> None:
        for line_no, content in added_lines:
            if TODO_PATTERN.search(content):
                signals.append(
                    CompletenessSignal(
                        type=CompletenessSignalType.TODO_DETECTED,
                        file_path=filename,
                        line_number=line_no,
                        evidence=content.strip(),
                        description=f"Potential completeness issue: TODO/FIXME detected in '{filename}' at line {line_no}.",
                    )
                )

    def _check_placeholders(
        self,
        filename: str,
        added_lines: List[Tuple[int, str]],
        full_patch: str,
        signals: List[CompletenessSignal],
    ) -> None:
        for i, (line_no, content) in enumerate(added_lines):
            stripped = content.strip()

            # Pattern A: Explicit NotImplementedError
            if "NotImplementedError" in content:
                signals.append(
                    CompletenessSignal(
                        type=CompletenessSignalType.PLACEHOLDER_DETECTED,
                        file_path=filename,
                        line_number=line_no,
                        evidence=stripped,
                        description=f"Potential placeholder detected: 'NotImplementedError' raised in '{filename}' at line {line_no}.",
                    )
                )
                continue

            # Pattern B: Suspicious pass or return in function definition
            # Avoid flagging empty class definitions (e.g. `class EmptyClass:` or `class Foo(Base): pass`)
            if stripped in ("pass", "...", "return", "return None") or stripped.startswith("return None #"):
                # Check previous line to see if it's a function definition vs class definition
                prev_line_content = added_lines[i - 1][1] if i > 0 else ""
                if prev_line_content:
                    prev_stripped = prev_line_content.strip()
                    # If preceded by a class definition, `pass` is valid and not a placeholder!
                    if prev_stripped.startswith("class ") or "class " in prev_stripped:
                        continue
                    # If preceded by def, it's a potential function stub placeholder
                    if prev_stripped.startswith("def ") or "def " in prev_stripped:
                        signals.append(
                            CompletenessSignal(
                                type=CompletenessSignalType.PLACEHOLDER_DETECTED,
                                file_path=filename,
                                line_number=line_no,
                                evidence=f"{prev_stripped} -> {stripped}",
                                description=f"Potential placeholder detected: Empty function stub in '{filename}' at line {line_no}.",
                            )
                        )

    def _check_error_handling(
        self,
        filename: str,
        added_lines: List[Tuple[int, str]],
        patch: str,
        signals: List[CompletenessSignal],
    ) -> None:
        # Check if patch contains risky operations without try/except context
        has_try_block = "try:" in patch or "except" in patch or "catch" in patch
        if has_try_block:
            return

        for line_no, content in added_lines:
            stripped = content.strip()
            # Ignore comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern, op_name in RISKY_OPS:
                if pattern.search(content):
                    signals.append(
                        CompletenessSignal(
                            type=CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING,
                            file_path=filename,
                            line_number=line_no,
                            evidence=stripped,
                            description=f"No obvious error-handling pattern detected around the modified {op_name} in '{filename}' at line {line_no}.",
                        )
                    )

    def _check_tests(
        self,
        context: CommitAnalysisContext,
        signals: List[CompletenessSignal],
    ) -> None:
        impl_files: List[str] = []
        test_files: List[str] = []

        for f in context.changed_files:
            if not isinstance(f, dict):
                continue
            path = f.get("filename", "")
            if not path:
                continue

            if path.startswith("tests/") or path.startswith("test/") or "test_" in path or "_test." in path:
                test_files.append(path)
            elif path.endswith((".py", ".js", ".ts", ".go", ".java", ".cpp")):
                impl_files.append(path)

        if test_files:
            signals.append(
                CompletenessSignal(
                    type=CompletenessSignalType.TEST_CHANGE_DETECTED,
                    evidence=f"Test files modified: {', '.join(test_files)}",
                    description="Test changes detected in commit.",
                )
            )

        if impl_files and not test_files:
            # Check repository context if available
            repo_ctx = context.repository_context
            has_repo_tests = False

            if repo_ctx and hasattr(repo_ctx, "files") and isinstance(repo_ctx.files, dict):
                has_repo_tests = any(
                    "test" in p.lower() for p in repo_ctx.files.keys()
                )
                if has_repo_tests:
                    signals.append(
                        CompletenessSignal(
                            type=CompletenessSignalType.MISSING_TEST_COVERAGE,
                            evidence=f"Implementation files modified ({', '.join(impl_files)}), but no test files modified.",
                            description="No corresponding test was detected in this commit.",
                        )
                    )
                else:
                    signals.append(
                        CompletenessSignal(
                            type=CompletenessSignalType.MISSING_TEST_COVERAGE,
                            evidence=f"Implementation files modified ({', '.join(impl_files)}), no tests in repository context.",
                            description="No tests exist in repository context.",
                        )
                    )
            else:
                # Evidence is insufficient to determine if tests exist in repo
                signals.append(
                    CompletenessSignal(
                        type=CompletenessSignalType.INSUFFICIENT_EVIDENCE,
                        evidence=f"Implementation files modified: {', '.join(impl_files)}.",
                        description="Evidence was insufficient to determine completeness of tests.",
                    )
                )

    def _check_documentation(
        self,
        context: CommitAnalysisContext,
        signals: List[CompletenessSignal],
    ) -> None:
        doc_files = [
            f.get("filename")
            for f in context.changed_files
            if isinstance(f, dict)
            and f.get("filename", "").endswith((".md", ".rst", ".txt"))
            or f.get("filename", "").startswith("docs/")
        ]

        if doc_files:
            signals.append(
                CompletenessSignal(
                    type=CompletenessSignalType.DOCUMENTATION_CHANGE_DETECTED,
                    evidence=f"Documentation files modified: {', '.join(filter(None, doc_files))}",
                    description="Documentation changes detected.",
                )
            )
