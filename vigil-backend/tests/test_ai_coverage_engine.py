import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.user import User
from app.schemas.ai_review import AIReviewResponse
from app.services.ai.context.builder import ReviewContextBuilder
from app.services.ai.context.schemas import (
    ChangedFileContext,
    RepositoryStructureContext,
    ReviewContext,
    ScannerFindingContext,
)
from app.services.ai.deep.orchestrator import DeepReviewOrchestrator
from app.services.ai.gateway import AIModelGateway
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.review.coverage import (
    compute_review_coverage,
    compute_review_limitations,
    compute_review_matrix,
)
from app.services.ai.review.engine import ReviewEngine
from app.services.ai.review.schemas import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    ReviewFinding,
    ReviewResult,
    ReviewStatus,
)
from app.services.ai.review.validator import ReviewValidator
from app.services.ai_review_service import AIReviewService


@compiles(UNIQUEIDENTIFIER, "sqlite")
def compile_uniqueidentifier_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_pr(db_session):
    user = User(github_user_id=1, github_login="dev", display_name="Dev")
    db_session.add(user)
    db_session.flush()

    repo = Repository(
        user_id=user.id,
        github_repo_id=10,
        owner_login="dev",
        name="repo",
        full_name="dev/repo",
        default_branch="main",
        private=False,
        html_url="https://github.com/dev/repo",
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=100,
        pr_number=1,
        title="Phase 3 Coverage Test PR",
        description="Testing coverage and matrix calculation",
        author_login="dev",
        source_branch="feat",
        target_branch="main",
        head_sha="sha1",
        base_sha="sha0",
        status="OPEN",
    )
    db_session.add(pr)
    db_session.flush()
    return pr


# 1. exact changed-file coverage calculation
def test_exact_changed_file_coverage_calculation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ print(1)")
    builder.add_changed_file("app/utils.py", diff_patch="+ print(2)")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.changed_files == {"total": 2, "reviewed": 2}
    assert cov.status_summary["changed_files"] == "YES"


# 2. exact changed-symbol coverage calculation
def test_exact_changed_symbol_coverage_calculation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ def run(): pass")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [], execution_meta={"symbols": ["run", "init_app"]})
    assert cov.changed_symbols == {"total": 2, "reviewed": 2}
    assert cov.status_summary["changed_symbols"] == "YES"


# 3. test coverage calculation
def test_test_coverage_calculation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/service.py", diff_patch="+ pass")
    builder.set_repository(
        file_paths=["app/service.py"],
        test_paths=["tests/test_service.py", "tests/test_auth.py"],
    )
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.tests_reviewed == 2
    assert cov.status_summary["tests"] == "YES"


# 4. dependency coverage calculation
def test_dependency_coverage_calculation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    builder.set_repository(
        file_paths=["app/main.py"],
        dependencies={"fastapi": "0.100.0", "pydantic": "2.0.0"},
    )
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.dependencies_reviewed == 2
    assert cov.status_summary["dependencies"] == "YES"


# 5. scanner-finding coverage calculation
def test_scanner_finding_coverage_calculation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ eval('x')")
    builder.add_scanner_finding(
        source="semgrep",
        category="security",
        severity="high",
        message="Use of eval",
        rule_id="python.eval",
        file_path="app/main.py",
        start_line=1,
    )
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.scanner_findings_reviewed == 1
    assert cov.status_summary["scanner_findings"] == "YES"


# 6. unavailable context handling
def test_unavailable_context_handling():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.changed_symbols is None
    assert cov.tests_reviewed is None
    assert cov.dependencies_reviewed is None
    assert cov.scanner_findings_reviewed is None
    assert cov.status_summary["changed_symbols"] == "UNAVAILABLE"
    assert cov.status_summary["tests"] == "UNAVAILABLE"
    assert cov.status_summary["dependencies"] == "UNAVAILABLE"
    assert cov.status_summary["scanner_findings"] == "UNAVAILABLE"


# 7. review matrix applicable category
def test_review_matrix_applicable_category():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/auth.py", diff_patch="+ def check_login(user, token): pass")
    context = builder.build(normalize=True)

    matrix = compute_review_matrix(context, [])
    matrix_map = {m.category: m for m in matrix}

    assert matrix_map["Security"].applicable is True
    assert matrix_map["Authorization"].applicable is True
    assert matrix_map["Authorization"].status == "YES"


# 8. review matrix not-applicable category
def test_review_matrix_not_applicable_category():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/utils.py", diff_patch="+ def add(a, b): return a + b")
    context = builder.build(normalize=True)

    matrix = compute_review_matrix(context, [])
    matrix_map = {m.category: m for m in matrix}

    assert matrix_map["Authorization"].applicable is False
    assert matrix_map["Authorization"].status == "N/A"
    assert "No authorization" in matrix_map["Authorization"].reason


# 9. review matrix genuinely unreviewed category
def test_review_matrix_genuinely_unreviewed_category():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    matrix = compute_review_matrix(context, [])
    for m in matrix:
        assert isinstance(m.reviewed, bool)
        assert m.status in ("YES", "NO", "N/A", "UNAVAILABLE")


# 10. evidence provenance retention
def test_evidence_provenance_retention():
    finding = ReviewFinding(
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="SQL Injection",
        file="app/db.py",
        line=10,
        problem="Raw query execution",
        why="Allows SQL injection attacks",
        evidence="query = f'SELECT * FROM users WHERE id = {user_id}'",
        source="AI-EvidenceChain",
        is_grounded=True,
    )

    assert finding.file == "app/db.py"
    assert finding.line == 10
    assert finding.evidence is not None
    assert finding.source == "AI-EvidenceChain"


# 11. grounded finding accepted
def test_grounded_finding_accepted():
    validator = ReviewValidator()
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ val = unsafe_call()")
    context = builder.build(normalize=True)

    raw_data = {
        "summary": "Check",
        "findings": [
            {
                "category": "Security",
                "severity": "high",
                "title": "Unsafe call",
                "file": "app/main.py",
                "line": 1,
                "problem": "Call is unsafe",
                "why": "Security risk",
                "evidence": "val = unsafe_call()",
            }
        ],
    }

    result = validator.validate(raw_data, context)
    assert len(result.findings) == 1
    assert result.findings[0].is_grounded is True


# 12. unsupported finding rejected
def test_unsupported_finding_rejected():
    validator = ReviewValidator(drop_hallucinated_files=True)
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ val = 1")
    context = builder.build(normalize=True)

    raw_data = {
        "summary": "Check",
        "findings": [
            {
                "category": "Security",
                "severity": "high",
                "title": "Hallucinated issue",
                "file": "nonexistent_file.py",
                "line": 99,
                "problem": "Fake problem",
                "why": "Fake risk",
            }
        ],
    }

    result = validator.validate(raw_data, context)
    assert len(result.findings) == 0
    assert result.validation_metadata["dropped_hallucinations"] == 1


# 13. severity independent from confidence
def test_severity_independent_from_confidence():
    finding1 = ReviewFinding(
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        confidence=FindingConfidence.LOW,
        title="Unverified critical claim",
        file="app/auth.py",
        problem="Claimed breach",
        why="Risk",
    )

    finding2 = ReviewFinding(
        category=FindingCategory.DOCUMENTATION,
        severity=FindingSeverity.INFO,
        confidence=FindingConfidence.HIGH,
        title="Verified typo",
        file="app/doc.py",
        problem="Typo",
        why="Readability",
        evidence="typo_line = True",
    )

    assert finding1.severity == FindingSeverity.CRITICAL
    assert finding1.confidence == FindingConfidence.LOW

    assert finding2.severity == FindingSeverity.INFO
    assert finding2.confidence == FindingConfidence.HIGH


# 14. HIGH severity + LOW confidence
def test_high_severity_low_confidence():
    finding = ReviewFinding(
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        confidence=FindingConfidence.LOW,
        title="Hypothetical remote exploit",
        file="app/net.py",
        problem="Possible buffer overflow without caller context",
        why="High potential impact",
    )
    assert finding.severity == FindingSeverity.HIGH
    assert finding.confidence == FindingConfidence.LOW


# 15. LOW severity + HIGH confidence
def test_low_severity_high_confidence():
    finding = ReviewFinding(
        category=FindingCategory.MAINTAINABILITY,
        severity=FindingSeverity.LOW,
        confidence=FindingConfidence.HIGH,
        title="Unused import",
        file="app/main.py",
        line=5,
        problem="Import unused",
        why="Clean code",
        evidence="import unused_mod",
        is_grounded=True,
    )
    assert finding.severity == FindingSeverity.LOW
    assert finding.confidence == FindingConfidence.HIGH


# 16. limitations generated from missing evidence
def test_limitations_generated_from_missing_evidence():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    limitations = compute_review_limitations(context)
    lim_categories = {l.category for l in limitations}

    assert "runtime" in lim_categories
    assert "external_api" in lim_categories
    assert "ast" in lim_categories
    assert "scanners" in lim_categories
    assert "testing" in lim_categories
    assert "git_history" in lim_categories


# 17. runtime-not-executed limitation
def test_runtime_not_executed_limitation():
    limitations = compute_review_limitations(None)
    runtime_lim = next(l for l in limitations if l.category == "runtime")

    assert runtime_lim.status == "NOT_EXECUTED"
    assert "Runtime behavior was not executed" in runtime_lim.limitation


# 18. unavailable API limitation
def test_unavailable_api_limitation():
    limitations = compute_review_limitations(None)
    api_lim = next(l for l in limitations if l.category == "external_api")

    assert api_lim.status == "UNAVAILABLE"
    assert "External API behavior was unavailable" in api_lim.limitation


# 19. unavailable scanner limitation
def test_unavailable_scanner_limitation():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    limitations = compute_review_limitations(context)
    scanner_lim = next(l for l in limitations if l.category == "scanners")

    assert scanner_lim.status == "UNAVAILABLE"
    assert "Scanner findings were unavailable" in scanner_lim.limitation


# 20. clean PR coverage reported honestly
def test_clean_pr_coverage_reported_honestly():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/clean.py", diff_patch="+ # clean comment change")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    matrix = compute_review_matrix(context, [])

    assert cov.changed_files == {"total": 1, "reviewed": 1}
    assert cov.final_findings == 0
    assert len(matrix) == 9


# 21. multi-file coverage
def test_multi_file_coverage():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/a.py", diff_patch="+ pass")
    builder.add_changed_file("app/b.py", diff_patch="+ pass")
    builder.add_changed_file("app/c.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [])
    assert cov.changed_files == {"total": 3, "reviewed": 3}


# 22. multi-symbol coverage
def test_multi_symbol_coverage():
    builder = ReviewContextBuilder()
    builder.add_changed_file("app/main.py", diff_patch="+ pass")
    context = builder.build(normalize=True)

    cov = compute_review_coverage(context, [], execution_meta={"symbols": ["func1", "func2", "func3", "ClassA"]})
    assert cov.changed_symbols == {"total": 4, "reviewed": 4}


# 23. deep-review coverage integration
@pytest.mark.asyncio
async def test_deep_review_coverage_integration():
    planner_json = json.dumps({
        "summary": "Plan summary",
        "strategy": "security-first",
        "targets": [{"file": "app/auth.py", "symbols": ["login"], "areas": ["security"], "priority": "high", "reason": "Auth focus"}]
    })
    broad_json = json.dumps({
        "summary": "Broad review",
        "candidates": [
            {
                "category": "Security",
                "severity_estimate": "high",
                "title": "SQL Injection",
                "file": "app/auth.py",
                "line": 10,
                "problem_hypothesis": "Raw SQL concatenation",
                "why_investigate": "SQL injection risk",
                "evidence": "SELECT * FROM users",
                "priority": "high",
            }
        ]
    })
    inv_json = json.dumps({
        "is_supported": True,
        "summary": "Grounded SQL injection confirmed",
        "finding": {
            "category": "Security",
            "severity": "high",
            "title": "SQL Injection",
            "file": "app/auth.py",
            "line": 10,
            "problem": "Raw SQL concatenation in auth logic",
            "why": "Unsanitized user input allows query manipulation",
            "evidence": "SELECT * FROM users",
            "suggestion": "Use parameterized queries",
        }
    })

    mock_provider = MockProvider(responses=[planner_json, broad_json, inv_json])
    gateway = AIModelGateway(provider=mock_provider)
    orchestrator = DeepReviewOrchestrator(gateway=gateway)

    builder = ReviewContextBuilder()
    builder.add_changed_file("app/auth.py", diff_patch="+ SELECT * FROM users")
    context = builder.build(normalize=True)

    result = await orchestrator.review(context)
    assert result.validation_metadata is not None
    assert "coverage" in result.validation_metadata
    assert result.validation_metadata["coverage"]["candidates_generated"] == 1


# 24. standard-review backward compatibility
@pytest.mark.asyncio
async def test_standard_review_backward_compatibility(db_session, seeded_pr):
    std_json = json.dumps({"summary": "Standard review summary", "status": "APPROVED", "findings": []})
    mock_provider = MockProvider(responses=[std_json])
    gateway = AIModelGateway(provider=mock_provider)
    review_engine = ReviewEngine(gateway=gateway)
    service = AIReviewService(review_engine=review_engine)

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        review_depth="standard",
    )
    assert isinstance(response, AIReviewResponse)
    assert response.review_depth == "standard"
    assert response.coverage is not None
    assert response.review_matrix is not None
    assert response.limitations is not None


# 25. API response contains coverage/matrix/limitations
@pytest.mark.asyncio
async def test_api_response_contains_coverage_matrix_limitations(db_session, seeded_pr):
    std_json = json.dumps({"summary": "Standard review summary", "status": "APPROVED", "findings": []})
    mock_provider = MockProvider(responses=[std_json])
    gateway = AIModelGateway(provider=mock_provider)
    review_engine = ReviewEngine(gateway=gateway)
    service = AIReviewService(review_engine=review_engine)

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        changed_files=[ChangedFileContext(file_path="app/main.py", diff_patch="+ print(1)")],
        review_depth="standard",
    )

    assert response.coverage is not None
    assert response.coverage["changed_files"] == {"total": 1, "reviewed": 1}
    assert response.review_matrix is not None
    assert len(response.review_matrix) == 9
    assert response.limitations is not None
    assert len(response.limitations) >= 5
