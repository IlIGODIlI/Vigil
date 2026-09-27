import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

@compiles(UNIQUEIDENTIFIER, "sqlite")
def compile_uniqueidentifier_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"

from app.db.base import Base
from app.models.commit import Commit
from app.models.commit_analysis import CommitAnalysis, CommitAnalysisOverallStatus, CommitAnalysisStatus
from app.models.repository import Repository
from app.models.user import User

from app.services.commit_analysis.ai_boundary import (
    CommitSemanticAnalyzerInterface,
    SafeAISemanticAnalyzerWrapper,
    StubCommitSemanticAnalyzer,
)
from app.services.commit_analysis.completeness_engine import CompletenessSignalEngine
from app.services.commit_analysis.deterministic_analyzer import DeterministicAnalyzer
from app.services.commit_analysis.intent_classifier import classify_commit_intent
from app.services.commit_analysis.schemas import (
    CompletenessSignal,
    CompletenessSignalType,
    CommitAnalysisContext,
    CommitIntent,
)
from app.services.commit_analysis.service import CommitAnalysisEngineService, commit_analysis_engine_service


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 1. Intent Classification Tests
# -----------------------------------------------------------------------------

def test_intent_classification_feature():
    intent = classify_commit_intent(
        message="feat: Add payment refund endpoint",
        changed_files=[{"filename": "app/api/refund.py"}],
    )
    assert intent == CommitIntent.FEATURE


def test_intent_classification_bug_fix():
    intent = classify_commit_intent(
        message="Fix null pointer exception in checkout flow",
        changed_files=[{"filename": "app/services/checkout.py"}],
    )
    assert intent == CommitIntent.BUG_FIX


def test_intent_classification_documentation():
    intent = classify_commit_intent(
        message="Update README with setup instructions",
        changed_files=[{"filename": "README.md"}],
    )
    assert intent == CommitIntent.DOCUMENTATION


def test_intent_classification_dependency_update():
    intent = classify_commit_intent(
        message="Bump FastAPI version to 0.100.0",
        changed_files=[{"filename": "requirements.txt"}],
    )
    assert intent == CommitIntent.DEPENDENCY_UPDATE


def test_intent_classification_test_only():
    intent = classify_commit_intent(
        message="Add tests for payment refund service",
        changed_files=[{"filename": "tests/test_refund.py"}],
    )
    assert intent == CommitIntent.TEST


def test_intent_classification_refactor():
    intent = classify_commit_intent(
        message="Refactor authentication service for efficiency",
        changed_files=[{"filename": "app/services/auth.py"}],
    )
    assert intent == CommitIntent.REFACTOR


def test_intent_classification_formatting():
    intent = classify_commit_intent(
        message="Format code with black",
        changed_files=[{"filename": "app/main.py"}],
        diff="only whitespace",
    )
    assert intent == CommitIntent.FORMATTING


def test_intent_classification_ambiguous_other():
    intent = classify_commit_intent(
        message="misc internal tweaks",
        changed_files=[{"filename": "app/utils.py"}],
    )
    assert intent == CommitIntent.OTHER


# -----------------------------------------------------------------------------
# 2. Deterministic Analyzer Tests (TODO, FIXME, Placeholders, Tests, Error Handling)
# -----------------------------------------------------------------------------

def test_todo_and_fixme_detection():
    analyzer = DeterministicAnalyzer()
    ctx = CommitAnalysisContext(
        commit_sha="sha1",
        commit_message="WIP feature",
        changed_files=[{
            "filename": "app/feature.py",
            "patch": "@@ -0,0 +1,5 @@\n+def process():\n+    # TODO: implement validation\n+    # FIXME: handle edge case\n+    pass",
        }],
    )
    signals = analyzer.analyze(ctx)
    todo_signals = [s for s in signals if s.type == CompletenessSignalType.TODO_DETECTED]
    assert len(todo_signals) >= 2
    assert "TODO" in todo_signals[0].evidence or "FIXME" in todo_signals[0].evidence


def test_not_implemented_error_detection():
    analyzer = DeterministicAnalyzer()
    ctx = CommitAnalysisContext(
        commit_sha="sha2",
        commit_message="Add stub method",
        changed_files=[{
            "filename": "app/service.py",
            "patch": "@@ -10,10 +10,12 @@\n def execute():\n+    raise NotImplementedError('Not ready')",
        }],
    )
    signals = analyzer.analyze(ctx)
    ph_signals = [s for s in signals if s.type == CompletenessSignalType.PLACEHOLDER_DETECTED]
    assert len(ph_signals) == 1
    assert "NotImplementedError" in ph_signals[0].evidence
    assert "Potential placeholder detected" in ph_signals[0].description


def test_suspicious_placeholder_function_stub():
    analyzer = DeterministicAnalyzer()
    ctx = CommitAnalysisContext(
        commit_sha="sha3",
        commit_message="Add stub function",
        changed_files=[{
            "filename": "app/handler.py",
            "patch": "@@ -0,0 +1,2 @@\n+def handle_request():\n+    pass",
        }],
    )
    signals = analyzer.analyze(ctx)
    ph_signals = [s for s in signals if s.type == CompletenessSignalType.PLACEHOLDER_DETECTED]
    assert len(ph_signals) == 1
    assert "Potential placeholder detected" in ph_signals[0].description


def test_false_positive_empty_class_pass():
    """Valid empty class declaration `class EmptyClass: pass` must NOT trigger placeholder warning."""
    analyzer = DeterministicAnalyzer()
    ctx = CommitAnalysisContext(
        commit_sha="sha4",
        commit_message="Add custom exception class",
        changed_files=[{
            "filename": "app/exceptions.py",
            "patch": "@@ -0,0 +1,2 @@\n+class CustomError(Exception):\n+    pass",
        }],
    )
    signals = analyzer.analyze(ctx)
    ph_signals = [s for s in signals if s.type == CompletenessSignalType.PLACEHOLDER_DETECTED]
    assert len(ph_signals) == 0  # No false positive!


def test_missing_error_handling_detection():
    analyzer = DeterministicAnalyzer()
    ctx = CommitAnalysisContext(
        commit_sha="sha5",
        commit_message="Add external HTTP call",
        changed_files=[{
            "filename": "app/client.py",
            "patch": "@@ -1,5 +1,6 @@\n def fetch_data():\n+    res = httpx.get('https://api.external.com/data')\n+    return res.json()",
        }],
    )
    signals = analyzer.analyze(ctx)
    err_signals = [s for s in signals if s.type == CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING]
    assert len(err_signals) == 1
    assert "No obvious error-handling pattern detected" in err_signals[0].description


# -----------------------------------------------------------------------------
# 3. Commit-Type-Aware Completeness Signal Engine Tests
# -----------------------------------------------------------------------------

def test_documentation_only_commit_no_false_missing_test_warning():
    engine = CompletenessSignalEngine()
    ctx = CommitAnalysisContext(
        commit_sha="doc1",
        commit_message="Update documentation",
        changed_files=[{"filename": "README.md", "patch": "@@ -1 +1 @@\n+# New section"}],
    )
    raw_signals = [
        CompletenessSignal(
            type=CompletenessSignalType.MISSING_TEST_COVERAGE,
            evidence="No test files modified.",
            description="No corresponding test was detected.",
        )
    ]
    result = engine.process(context=ctx, intent=CommitIntent.DOCUMENTATION, signals=raw_signals)
    assert result.overall_status == CommitAnalysisOverallStatus.NO_SIGNIFICANT_GAPS
    assert not any(s.type == CompletenessSignalType.MISSING_TEST_COVERAGE for s in result.completeness_signals)
    assert "Tests not required" in result.testing_notes


def test_formatting_only_commit_no_irrelevant_warnings():
    engine = CompletenessSignalEngine()
    ctx = CommitAnalysisContext(
        commit_sha="fmt1",
        commit_message="Format code",
        changed_files=[{"filename": "app/main.py", "patch": "@@ -1 +1 @@\n-x=1\n+x = 1"}],
    )
    raw_signals = [
        CompletenessSignal(
            type=CompletenessSignalType.NO_OBVIOUS_ERROR_HANDLING,
            evidence="x = 1",
            description="No obvious error-handling pattern detected",
        )
    ]
    result = engine.process(context=ctx, intent=CommitIntent.FORMATTING, signals=raw_signals)
    assert result.overall_status == CommitAnalysisOverallStatus.NO_SIGNIFICANT_GAPS
    assert len(result.completeness_signals) == 0


def test_test_only_commit_no_false_missing_implementation_warning():
    engine = CompletenessSignalEngine()
    ctx = CommitAnalysisContext(
        commit_sha="test1",
        commit_message="Add unit tests",
        changed_files=[{"filename": "tests/test_auth.py", "patch": "@@ -0,0 +1,5 @@\n+def test_login(): pass"}],
    )
    result = engine.process(context=ctx, intent=CommitIntent.TEST, signals=[])
    assert result.overall_status == CommitAnalysisOverallStatus.NO_SIGNIFICANT_GAPS
    assert "Test-only commit" in result.implementation_notes


def test_feature_commit_missing_tests_needs_review():
    engine = CompletenessSignalEngine()
    ctx = CommitAnalysisContext(
        commit_sha="feat1",
        commit_message="Add new feature endpoint",
        changed_files=[{"filename": "app/api/feat.py", "patch": "@@ -0,0 +1,10 @@\n+def new_endpoint(): return True"}],
    )
    raw_signals = [
        CompletenessSignal(
            type=CompletenessSignalType.MISSING_TEST_COVERAGE,
            evidence="Implementation files modified, no test files modified.",
            description="No corresponding test was detected in this commit.",
        )
    ]
    result = engine.process(context=ctx, intent=CommitIntent.FEATURE, signals=raw_signals)
    assert result.overall_status == CommitAnalysisOverallStatus.NEEDS_REVIEW
    assert "No corresponding test was detected" in result.testing_notes


def test_insufficient_evidence_empty_context():
    engine = CompletenessSignalEngine()
    ctx = CommitAnalysisContext(
        commit_sha="empty1",
        commit_message="",
        changed_files=[],
    )
    result = engine.process(context=ctx, intent=CommitIntent.OTHER, signals=[])
    assert result.overall_status == CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE


# -----------------------------------------------------------------------------
# 4. AI Boundary Failure Graceful Handling Test
# -----------------------------------------------------------------------------

def test_ai_unavailable_mock_failure_graceful_degradation():
    class FailingAIAnalyzer(CommitSemanticAnalyzerInterface):
        async def analyze_semantic_consistency(self, context: CommitAnalysisContext):
            raise RuntimeError("Groq API 503 Service Unavailable")

    async def run_test():
        safe_wrapper = SafeAISemanticAnalyzerWrapper(FailingAIAnalyzer())
        ctx = CommitAnalysisContext(commit_sha="ai_fail", commit_message="test")
        return await safe_wrapper.analyze_semantic_consistency(ctx)

    res = asyncio.run(run_test())
    assert "failed" in res.lower() or "unavailable" in res.lower()


# -----------------------------------------------------------------------------
# 5. DB & End-to-End Orchestrator Integration Test
# -----------------------------------------------------------------------------

def test_full_commit_analysis_service_integration(db_session):
    user = User(
        id=uuid.uuid4(),
        github_user_id=12345,
        github_login="testuser",
        email="dev@example.com",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    repo = Repository(
        id=uuid.uuid4(),
        user_id=user.id,
        github_repo_id=999888,
        owner_login="testorg",
        name="testrepo",
        full_name="testorg/testrepo",
        default_branch="main",
        private=False,
        html_url="https://github.com/testorg/testrepo",
    )
    db_session.add(repo)
    db_session.flush()

    commit = Commit(
        id=uuid.uuid4(),
        repository_id=repo.id,
        sha="abc123def4567890123456789012345678901234",
        message="feat: Add new user profile API\n\n# TODO: add rate limiting",
        author_name="Developer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(commit)
    db_session.commit()

    result = commit_analysis_engine_service.trigger_commit_analysis_sync(
        db=db_session, sha=commit.sha
    )

    assert result is not None
    assert result.commit_id == commit.id
    assert result.status == CommitAnalysisStatus.COMPLETED.value
    assert result.overall_status in (
        CommitAnalysisOverallStatus.NEEDS_REVIEW.value,
        CommitAnalysisOverallStatus.NO_SIGNIFICANT_GAPS.value,
        CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE.value,
    )
    assert result.summary is not None
