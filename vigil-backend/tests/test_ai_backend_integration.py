import asyncio
from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import ResourceNotFoundException
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import Analysis, AnalysisStatus, AnalysisTrigger
from app.models.commit import Commit
from app.models.finding import Finding, FindingCategory, FindingSeverity, FindingSource, FindingStatus
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review import Review, ReviewStatus as DBReviewStatus
from app.models.user import User
from app.schemas.ai_review import AIReviewRequest, AIReviewResponse
from app.services.ai.context.schemas import ChangedFileContext, ScannerFindingContext
from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.gateway import AIModelGateway
from app.services.ai.providers.mock_provider import MockProvider
from app.services.ai.review.engine import ReviewEngine
from app.services.ai.review.schemas import ReviewStatus
from app.services.ai_review_service import AIReviewService, ai_review_service
from app.services.review_service import review_service


@compiles(UNIQUEIDENTIFIER, "sqlite")
def compile_uniqueidentifier_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@pytest.fixture
def db_session():
    """Provides a fresh isolated in-memory SQLite database populated with all VIGIL schemas."""
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
    """Seeds a representative VIGIL User, Repository, PullRequest, Commit, and Analysis with findings."""
    user = User(
        github_user_id=1001,
        github_login="octocat",
        display_name="The Octocat",
        email="octocat@github.com",
    )
    db_session.add(user)
    db_session.flush()

    repo = Repository(
        user_id=user.id,
        github_repo_id=2001,
        owner_login="octocat",
        name="vigil-repo",
        full_name="octocat/vigil-repo",
        default_branch="main",
        private=False,
        html_url="https://github.com/octocat/vigil-repo",
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=3001,
        pr_number=42,
        title="Sanitize SQL query in user search",
        description="Fixes SQL injection flaw in search parameters.",
        author_login="alice",
        source_branch="fix/sql-injection",
        target_branch="main",
        head_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        base_sha="f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5",
        status="OPEN",
    )
    db_session.add(pr)
    db_session.flush()

    commit = Commit(
        repository_id=repo.id,
        sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        message="feat: parameterize database query",
        author_login="alice",
        committed_at=datetime.now(timezone.utc),
    )
    db_session.add(commit)
    pr.commits.append(commit)
    db_session.flush()

    analysis = Analysis(
        pull_request_id=pr.id,
        head_sha=pr.head_sha,
        status=AnalysisStatus.COMPLETED.value,
        trigger_type=AnalysisTrigger.WEBHOOK.value,
    )
    db_session.add(analysis)
    db_session.flush()

    semgrep_finding = Finding(
        analysis_id=analysis.id,
        source=FindingSource.SEMGREP.value,
        category=FindingCategory.SECURITY.value,
        severity=FindingSeverity.HIGH.value,
        rule_id="python.lang.security.audit.raw-sql",
        fingerprint="semgrep-raw-sql-001",
        file_path="app/services/user_search.py",
        start_line=15,
        end_line=15,
        message="Detected potential SQL injection via string formatting.",
        status=FindingStatus.OPEN.value,
        evidence={"raw": "db.execute(f'SELECT * FROM users WHERE name = {query}')"},
    )
    db_session.add(semgrep_finding)
    db_session.commit()

    return pr


def test_build_review_context_from_existing_vigil_data(db_session, seeded_pr):
    """Verifies that ReviewContextBuilder accurately translates VIGIL DB models into ReviewContext."""
    service = AIReviewService()
    pr, context = service.build_review_context_for_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
    )

    # 1. Pull Request mapping
    assert context.pull_request is not None
    assert context.pull_request.title == seeded_pr.title
    assert context.pull_request.author == "alice"
    assert context.pull_request.pr_number == 42
    assert context.pull_request.head_sha == seeded_pr.head_sha

    # 2. Repository mapping
    assert context.repository is not None
    assert context.repository.repository_name == "octocat/vigil-repo"

    # 3. Commits mapping
    assert len(context.commits) == 1
    assert context.commits[0].sha == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    assert context.commits[0].message == "feat: parameterize database query"

    # 4. Scanner findings mapping (from DB Semgrep finding)
    assert len(context.scanner_findings) == 1
    assert context.scanner_findings[0].source == "SEMGREP"
    assert context.scanner_findings[0].file_path == "app/services/user_search.py"

    # 5. Upstream missing data remains uninvented
    assert len(context.changed_files) == 0


@pytest.mark.asyncio
async def test_successful_pr_ai_review_execution(db_session, seeded_pr):
    """Verifies end-to-end execution of AIReviewService with a mock provider."""
    mock_json = """
    {
      "summary": "Verified user lookup query fix; SQL injection vulnerability resolved.",
      "findings": [
        {
          "title": "Use parameterized query",
          "problem": "Raw SQL query uses string interpolation.",
          "why": "Allows SQL injection.",
          "file": "app/services/user_search.py",
          "line": 15,
          "category": "SECURITY",
          "severity": "HIGH",
          "evidence": "+ cursor.execute(query, (user_id,))",
          "suggestion": "Use db.execute(query, (user_id,))"
        }
      ]
    }
    """
    mock_provider = MockProvider(default_response=mock_json)
    engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))
    service = AIReviewService(review_engine=engine)

    changed_files = [
        ChangedFileContext(
            file_path="app/services/user_search.py",
            diff_patch="+ cursor.execute(query, (user_id,))",
        )
    ]

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        changed_files=changed_files,
        persist=False,
    )

    assert isinstance(response, AIReviewResponse)
    assert response.pull_request_id == seeded_pr.id
    assert response.status == ReviewStatus.SUCCESS.value
    assert "Verified user lookup query fix" in response.summary
    assert response.findings_count == 1
    assert response.grounded_findings == 1
    assert response.dropped_findings == 0
    assert response.findings[0].category.value.upper() == "SECURITY"
    assert response.findings[0].file == "app/services/user_search.py"


@pytest.mark.asyncio
async def test_hallucinated_finding_rejected_in_backend_service(db_session, seeded_pr):
    """Verifies that findings citing files outside the review context are pruned by ReviewValidator."""
    mock_json = """
    {
      "summary": "Review produced a hallucinated finding outside PR scope.",
      "findings": [
        {
          "title": "Insecure session management",
          "problem": "Cookie lacks HttpOnly flag.",
          "why": "Exposes session token to XSS attacks.",
          "file": "app/auth/cookies.py",
          "line": 88,
          "category": "SECURITY",
          "severity": "CRITICAL"
        }
      ]
    }
    """
    mock_provider = MockProvider(default_response=mock_json)
    engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))
    service = AIReviewService(review_engine=engine)

    # Changed files only contains user_search.py, not cookies.py
    changed_files = [
        ChangedFileContext(
            file_path="app/services/user_search.py",
            diff_patch="--- a/user_search.py\n+++ b/user_search.py\n@@ -1,1 +1,1 @@\n-old\n+new",
        )
    ]

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        changed_files=changed_files,
        persist=False,
    )

    # cookies.py is a hallucinated file -> must be dropped
    assert response.findings_count == 0
    assert response.dropped_findings == 1
    assert any("Dropped hallucinated finding" in w for w in response.warnings)


@pytest.mark.asyncio
async def test_persistence_creates_review_and_findings(db_session, seeded_pr):
    """Verifies that persist=True records Review and Finding models into the database."""
    mock_json = """
    {
      "summary": "Database persistence verified.",
      "findings": [
        {
          "title": "Missing index on lookup column",
          "problem": "Column should have a database index.",
          "why": "Full table scan causes performance degradation.",
          "file": "app/models/user.py",
          "line": 45,
          "category": "PERFORMANCE",
          "severity": "MEDIUM",
          "evidence": "+ email: str",
          "suggestion": "Add index=True"
        }
      ]
    }
    """
    mock_provider = MockProvider(default_response=mock_json)
    engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))
    service = AIReviewService(review_engine=engine)

    changed_files = [
        ChangedFileContext(
            file_path="app/models/user.py",
            diff_patch="+ email: str",
        )
    ]

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        changed_files=changed_files,
        persist=True,
    )

    assert response.review_id is not None

    # Query DB to verify Review model
    db_review = db_session.get(Review, response.review_id)
    assert db_review is not None
    assert db_review.status == DBReviewStatus.READY.value
    assert db_review.summary == "Database persistence verified."

    # Query DB to verify Finding model
    db_findings = (
        db_session.query(Finding)
        .filter(Finding.source == FindingSource.AI_REVIEW.value)
        .all()
    )
    assert len(db_findings) == 1
    assert db_findings[0].category == FindingCategory.PERFORMANCE.value
    assert db_findings[0].severity == FindingSeverity.MEDIUM.value
    assert db_findings[0].file_path == "app/models/user.py"
    assert db_findings[0].status == FindingStatus.OPEN.value
    assert db_findings[0].evidence["suggestion"] == "Add index=True"


@pytest.mark.asyncio
async def test_missing_pull_request_raises_not_found(db_session):
    """Verifies that an unknown PR UUID raises ResourceNotFoundException."""
    service = AIReviewService()
    fake_id = uuid.uuid4()

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await service.review_pull_request(
            db=db_session,
            pull_request_id=fake_id,
        )

    assert f"Pull request with ID '{fake_id}' not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_ai_output_handled_gracefully(db_session, seeded_pr):
    """Verifies that malformed or non-JSON output from the AI model does not crash the service."""
    raw_text = "I reviewed the code and found no issues, but I forgot to output JSON."
    mock_provider = MockProvider(default_response=raw_text)
    engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))
    service = AIReviewService(review_engine=engine)

    response = await service.review_pull_request(
        db=db_session,
        pull_request_id=seeded_pr.id,
        persist=False,
    )

    assert response.status in (ReviewStatus.WARNING.value, ReviewStatus.MALFORMED_OUTPUT.value)
    assert "Plain text fallback" in response.warnings[0] or len(response.warnings) > 0
    assert response.findings_count == 0


@pytest.mark.asyncio
async def test_review_service_delegates_to_ai_review_service(db_session, seeded_pr):
    """Verifies that review_service.execute_ai_review forwards seamlessly to AIReviewService."""
    mock_json = '{"summary": "Delegated review check.", "findings": []}'
    mock_provider = MockProvider(default_response=mock_json)
    custom_engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))

    # Temporarily inject custom engine
    original_engine = ai_review_service.review_engine
    ai_review_service.review_engine = custom_engine

    try:
        response = await review_service.execute_ai_review(
            db=db_session,
            pull_request_id=seeded_pr.id,
            custom_instructions="Focus on performance",
        )
        assert response.summary == "Delegated review check."
        assert response.status == ReviewStatus.SUCCESS.value
    finally:
        ai_review_service.review_engine = original_engine


def test_api_endpoint_pull_request_ai_review_success(db_session, seeded_pr):
    """Verifies that POST /api/v1/pull-requests/{id}/ai-review returns HTTP 200 with AIReviewResponse."""
    mock_json = """
    {
      "summary": "API endpoint review verified.",
      "findings": [
        {
          "title": "Unparameterized SQL call",
          "problem": "SQL injection vector via user input.",
          "why": "Attacker can execute arbitrary SQL statements.",
          "file": "app/services/user_search.py",
          "line": 15,
          "category": "SECURITY",
          "severity": "HIGH",
          "evidence": "+ cursor.execute(query, (user_id,))"
        }
      ]
    }
    """
    mock_provider = MockProvider(default_response=mock_json)
    custom_engine = ReviewEngine(gateway=AIModelGateway(provider=mock_provider))

    original_engine = ai_review_service.review_engine
    ai_review_service.review_engine = custom_engine

    # Override get_db in FastAPI app
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        payload = {
            "custom_instructions": "Check for injection",
            "persist": False,
            "changed_files": [
                {
                    "file_path": "app/services/user_search.py",
                    "diff_patch": "+ cursor.execute(query, (user_id,))",
                }
            ],
        }

        res = client.post(
            f"/api/v1/pull-requests/{seeded_pr.id}/ai-review",
            json=payload,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["pull_request_id"] == str(seeded_pr.id)
        assert data["summary"] == "API endpoint review verified."
        assert data["findings_count"] == 1
        assert data["findings"][0]["category"].upper() == "SECURITY"
        assert data["grounded_findings"] == 1
        assert data["dropped_findings"] == 0
    finally:
        app.dependency_overrides.clear()
        ai_review_service.review_engine = original_engine


def test_api_endpoint_pull_request_not_found(db_session):
    """Verifies that POST /api/v1/pull-requests/{id}/ai-review returns HTTP 404 for unknown PR."""
    fake_id = str(uuid.uuid4())

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        res = client.post(f"/api/v1/pull-requests/{fake_id}/ai-review")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_configuration_error_handled_safely(db_session, seeded_pr):
    """Verifies that missing AI configuration raises AIConfigurationError without leaking secrets."""
    class FailingConfigGateway(AIModelGateway):
        async def complete(self, request):
            raise AIConfigurationError("AI API key is missing or invalid")

    engine = ReviewEngine(gateway=FailingConfigGateway(provider=MockProvider()))
    service = AIReviewService(review_engine=engine)

    with pytest.raises(AIConfigurationError) as exc_info:
        await service.review_pull_request(
            db=db_session,
            pull_request_id=seeded_pr.id,
        )

    assert exc_info.value.status_code == 500
    assert "missing or invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ai_timeout_error_handled_safely(db_session, seeded_pr):
    """Verifies that an upstream AI provider timeout raises AITimeoutError (HTTP 504)."""
    class TimingOutGateway(AIModelGateway):
        async def complete(self, request):
            raise AITimeoutError("Upstream model request timed out after 60.0s")

    engine = ReviewEngine(gateway=TimingOutGateway(provider=MockProvider()))
    service = AIReviewService(review_engine=engine)

    with pytest.raises(AITimeoutError) as exc_info:
        await service.review_pull_request(
            db=db_session,
            pull_request_id=seeded_pr.id,
        )

    assert exc_info.value.status_code == 504
    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ai_provider_error_handled_safely(db_session, seeded_pr):
    """Verifies that provider connectivity errors raise AIProviderError (HTTP 502)."""
    class FailingProviderGateway(AIModelGateway):
        async def complete(self, request):
            raise AIProviderError("Upstream provider returned HTTP 503 Service Unavailable")

    engine = ReviewEngine(gateway=FailingProviderGateway(provider=MockProvider()))
    service = AIReviewService(review_engine=engine)

    with pytest.raises(AIProviderError) as exc_info:
        await service.review_pull_request(
            db=db_session,
            pull_request_id=seeded_pr.id,
        )

    assert exc_info.value.status_code == 502
    assert "Service Unavailable" in str(exc_info.value)


def test_api_endpoint_handles_ai_timeout_gracefully(db_session, seeded_pr):
    """Verifies that when AI times out, the FastAPI endpoint returns HTTP 504 via exception handler."""
    class TimingOutGateway(AIModelGateway):
        async def complete(self, request):
            raise AITimeoutError("AI gateway timeout")

    custom_engine = ReviewEngine(gateway=TimingOutGateway(provider=MockProvider()))
    original_engine = ai_review_service.review_engine
    ai_review_service.review_engine = custom_engine

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        res = client.post(f"/api/v1/pull-requests/{seeded_pr.id}/ai-review")
        assert res.status_code == 504
        assert "timeout" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
        ai_review_service.review_engine = original_engine
