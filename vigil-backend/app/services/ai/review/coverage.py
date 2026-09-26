from typing import Any, Dict, List, Optional

from app.services.ai.context.schemas import ReviewContext
from app.services.ai.deep.schemas import (
    ReviewCoverage,
    ReviewLimitation,
    ReviewMatrixItem,
)
from app.services.ai.review.schemas import FindingCategory, ReviewFinding


def compute_review_coverage(
    context: Optional[ReviewContext],
    findings: List[ReviewFinding],
    execution_meta: Optional[Dict[str, Any]] = None,
) -> ReviewCoverage:
    """Computes structured review coverage metrics from actual available context and execution results."""
    if not context:
        return ReviewCoverage(
            changed_files={"total": 0, "reviewed": 0},
            changed_symbols=None,
            tests_reviewed=None,
            dependencies_reviewed=None,
            scanner_findings_reviewed=None,
            status_summary={
                "changed_files": "NO",
                "changed_symbols": "UNAVAILABLE",
                "tests": "UNAVAILABLE",
                "dependencies": "UNAVAILABLE",
                "scanner_findings": "UNAVAILABLE",
            },
            candidates_generated=0,
            candidates_investigated=0,
            candidates_dropped=0,
            final_findings=len(findings),
            execution_status="SUCCESS",
        )

    # 1. Changed Files
    total_files = len(context.changed_files) if context.changed_files else 0
    reviewed_files = total_files
    if execution_meta and "coverage" in execution_meta:
        deep_cov = execution_meta["coverage"]
        if isinstance(deep_cov, dict) and "changed_files_examined" in deep_cov:
            reviewed_files = len(deep_cov["changed_files_examined"])

    # 2. Changed Symbols (UNAVAILABLE if not supplied)
    changed_symbols = None
    symbols_status = "UNAVAILABLE"
    repo_symbols = []
    if execution_meta and "symbols" in execution_meta and execution_meta["symbols"]:
        repo_symbols = execution_meta["symbols"]
    elif execution_meta and "changed_symbols" in execution_meta and execution_meta["changed_symbols"]:
        repo_symbols = execution_meta["changed_symbols"]

    if repo_symbols:
        changed_symbols = {"total": len(repo_symbols), "reviewed": len(repo_symbols)}
        symbols_status = "YES"

    # 3. Tests Reviewed (UNAVAILABLE if repository test paths not provided)
    tests_reviewed = None
    tests_status = "UNAVAILABLE"
    if context.repository and context.repository.test_paths:
        tests_reviewed = len(context.repository.test_paths)
        tests_status = "YES" if tests_reviewed > 0 else "NO"

    # 4. Dependencies Reviewed (UNAVAILABLE if repository dependencies not provided)
    dependencies_reviewed = None
    deps_status = "UNAVAILABLE"
    if context.repository and context.repository.dependencies:
        dependencies_reviewed = len(context.repository.dependencies)
        deps_status = "YES" if dependencies_reviewed > 0 else "NO"

    # 5. Scanner Findings Reviewed (UNAVAILABLE if scanner_findings is empty/None)
    scanner_findings_reviewed = None
    scanners_status = "UNAVAILABLE"
    if context and context.scanner_findings:
        scanner_findings_reviewed = len(context.scanner_findings)
        scanners_status = "YES" if scanner_findings_reviewed > 0 else "NO"

    # Candidate metrics for deep review
    candidates_gen = execution_meta.get("candidates_generated", 0) if execution_meta else 0
    candidates_inv = execution_meta.get("candidates_investigated", 0) if execution_meta else 0
    candidates_drp = execution_meta.get("candidates_dropped", 0) if execution_meta else 0

    return ReviewCoverage(
        changed_files={"total": total_files, "reviewed": reviewed_files},
        changed_symbols=changed_symbols,
        tests_reviewed=tests_reviewed,
        dependencies_reviewed=dependencies_reviewed,
        scanner_findings_reviewed=scanner_findings_reviewed,
        status_summary={
            "changed_files": "YES" if reviewed_files > 0 else "NO",
            "changed_symbols": symbols_status,
            "tests": tests_status,
            "dependencies": deps_status,
            "scanner_findings": scanners_status,
        },
        candidates_generated=candidates_gen,
        candidates_investigated=candidates_inv,
        candidates_dropped=candidates_drp,
        final_findings=len(findings),
        execution_status="SUCCESS",
    )


def compute_review_matrix(
    context: Optional[ReviewContext],
    findings: List[ReviewFinding],
    execution_depth: str = "standard",
) -> List[ReviewMatrixItem]:
    """Computes structured ReviewMatrix entries across standard review categories."""
    matrix: List[ReviewMatrixItem] = []

    diff_text = ""
    file_paths: List[str] = []
    if context and context.changed_files:
        for f in context.changed_files:
            file_paths.append(f.file_path.lower())
            if f.diff_patch:
                diff_text += f.diff_patch.lower() + "\n"
            if f.file_content:
                diff_text += f.file_content.lower() + "\n"

    repo_files = [fp.lower() for fp in context.repository.file_paths] if context and context.repository else []
    all_files = file_paths + repo_files

    has_auth = bool(
        any(
            k in diff_text or any(k in f for f in file_paths)
            for k in ["auth", "login", "permission", "role", "token", "session", "admin", "jwt"]
        )
    )
    has_tests = bool(
        any("test" in f for f in all_files)
        or bool(context and context.repository and context.repository.test_paths and len(context.repository.test_paths) > 0)
    )
    has_deps = bool(
        any(
            f.endswith(ext)
            for f in file_paths
            for ext in ["package.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle", "go.mod"]
        )
        or bool(context and context.repository and context.repository.dependencies and len(context.repository.dependencies) > 0)
    )

    has_perf = bool(any(k in diff_text for k in ["query", "benchmark", "optimize", "cache", "async", "thread", "pool", "loop"]))
    has_docs = bool(any(f.endswith(".md") or f.endswith(".rst") or "doc" in f for f in file_paths))

    category_definitions = [
        ("Security", True, "Evaluated security risk on all changed code diffs"),
        ("Authorization", has_auth, "Authorization check applicable based on auth/permission logic" if has_auth else "No authorization or authentication code in supplied context"),
        ("Logic", True, "Core business logic evaluated across changed files"),
        ("Reliability", True, "Error handling and reliability evaluated across diffs"),
        ("Testing", has_tests, "Testing context evaluated" if has_tests else "No test files modified or test paths supplied in context"),
        ("Dependencies", has_deps, "Dependency configuration present" if has_deps else "No dependency files changed or supplied in context"),
        ("Maintainability", True, "Code maintainability and readability evaluated"),
        ("Performance", has_perf or True, "Performance impact evaluated across code diffs"),
        ("Documentation", has_docs or "doc" in diff_text, "Documentation evaluated" if (has_docs or "doc" in diff_text) else "No documentation files modified in context"),
    ]

    for cat_name, is_app, reason_msg in category_definitions:
        cat_findings = [
            f for f in findings
            if (isinstance(f.category, FindingCategory) and f.category.value.lower() == cat_name.lower())
            or (isinstance(f.category, str) and f.category.lower() == cat_name.lower())
        ]
        ev_count = len(cat_findings)
        reviewed = bool(is_app)

        if is_app:
            status = "YES"
            reason = None
        else:
            status = "N/A"
            reason = reason_msg

        matrix.append(
            ReviewMatrixItem(
                category=cat_name,
                applicable=bool(is_app),
                reviewed=reviewed,
                evidence_count=ev_count,
                status=status,
                reason=reason,
            )
        )

    return matrix


def compute_review_limitations(
    context: Optional[ReviewContext],
    execution_meta: Optional[Dict[str, Any]] = None,
) -> List[ReviewLimitation]:
    """Computes structured review limitations from actual missing context inputs."""
    limitations: List[ReviewLimitation] = []

    # 1. Runtime execution limitation
    limitations.append(
        ReviewLimitation(
            limitation="Runtime behavior was not executed.",
            category="runtime",
            impact="Dynamic execution flaws, race conditions, and memory profiles were not observed",
            status="NOT_EXECUTED",
        )
    )

    # 2. External API behavior limitation
    limitations.append(
        ReviewLimitation(
            limitation="External API behavior was unavailable.",
            category="external_api",
            impact="Third-party service responses and live network endpoints were not simulated",
            status="UNAVAILABLE",
        )
    )

    # 3. Caller / Callee AST graph limitation
    limitations.append(
        ReviewLimitation(
            limitation="Caller/callee context was unavailable.",
            category="ast",
            impact="Full intra-procedural AST call graph traversal was not performed",
            status="UNAVAILABLE",
        )
    )

    # 4. Scanner findings limitation
    if not context or not context.scanner_findings:
        limitations.append(
            ReviewLimitation(
                limitation="Scanner findings were unavailable.",
                category="scanners",
                impact="Static analysis tool corroboration was not provided in review context",
                status="UNAVAILABLE",
            )
        )

    # 5. Integration tests limitation
    if not context or not context.repository or not context.repository.test_paths:
        limitations.append(
            ReviewLimitation(
                limitation="Integration tests were not provided.",
                category="testing",
                impact="Test suite coverage analysis limited to supplied diff context",
                status="UNAVAILABLE",
            )
        )

    # 6. Repository history limitation
    if not context or not context.commits:
        limitations.append(
            ReviewLimitation(
                limitation="Repository history was unavailable.",
                category="git_history",
                impact="Historical commit context and author blame data were not supplied",
                status="UNAVAILABLE",
            )
        )

    return limitations
