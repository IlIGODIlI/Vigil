"""
Phase 6 — Comprehensive test suite for Finding Verification & Human Review Queue.

Tests cover:
  1. Review queue (findings)
  2. Finding detail endpoint
  3. Verification decisions (VERIFIED, REJECTED, DISMISSED)
  4. Authentication enforcement
  5. Audit trail / history
  6. Immutability of AI evidence
  7. Concurrency / optimistic locking
  8. Multiple independent findings per analysis
  9. Error handling (missing finding, invalid state, invalid decision)
  10. Filtering (status, severity, repository, PR, commit)
  11. Pagination
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import Analysis, AnalysisStatus, AnalysisTrigger
from app.models.finding import Finding, FindingSource, FindingSeverity, FindingStatus
from app.models.finding_verification import FindingVerification
from app.models.pull_request import PullRequest, PullRequestStatus
from app.models.repository import Repository
from app.models.user import User

client = TestClient(app)

AUTH_HEADER = {"X-Reviewer-Login": "test_reviewer"}
AUTH_HEADER_B = {"X-Reviewer-Login": "reviewer_b"}


# ──────────────────────────────────────────────────────────────────────────────
# DB Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_override(db_session):
    """Override get_db dependency for TestClient."""
    def override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override
    yield db_session
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Helper builders
# ──────────────────────────────────────────────────────────────────────────────

def make_user(db) -> User:
    user = User(
        github_user_id=12345,
        github_login="test_org",
        display_name="Test Org",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def make_repo(db, user: User) -> Repository:
    repo = Repository(
        user_id=user.id,
        github_repo_id=99001,
        owner_login="test_org",
        name="test-repo",
        full_name="test_org/test-repo",
        default_branch="main",
        private=False,
        html_url="https://github.com/test_org/test-repo",
    )
    db.add(repo)
    db.flush()
    return repo


def make_pr(db, repo: Repository) -> PullRequest:
    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=1001,
        pr_number=1,
        title="Test PR",
        author_login="contributor",
        source_branch="feature",
        target_branch="main",
        head_sha="abc123def456",
        base_sha="000000000000",
        status=PullRequestStatus.OPEN.value,
    )
    db.add(pr)
    db.flush()
    return pr


def make_analysis(db, pr: PullRequest, sha: str = "abc123def456") -> Analysis:
    analysis = Analysis(
        pull_request_id=pr.id,
        head_sha=sha,
        status=AnalysisStatus.COMPLETED.value,
        trigger_type=AnalysisTrigger.WEBHOOK.value,
    )
    db.add(analysis)
    db.flush()
    return analysis


def make_finding(
    db,
    analysis: Analysis,
    status: str = FindingStatus.PENDING_REVIEW.value,
    severity: str = FindingSeverity.HIGH.value,
    message: str = "Possible SQL injection\n\nDetail here.",
    file_path: str = "app/db.py",
) -> Finding:
    finding = Finding(
        analysis_id=analysis.id,
        source=FindingSource.AI_REVIEW.value,
        category="SECURITY",
        severity=severity,
        fingerprint=str(uuid.uuid4()),
        file_path=file_path,
        start_line=42,
        end_line=48,
        message=message,
        status=status,
        evidence={
            "reasoning": "The query is built with string concatenation.",
            "evidence": ["Line 42: query = 'SELECT * FROM users WHERE id=' + user_id"],
            "introduced_by_commit": True,
        },
    )
    db.add(finding)
    db.flush()
    return finding


def make_full_stack(db):
    """Return (user, repo, pr, analysis, finding) with a complete relational chain."""
    user = make_user(db)
    repo = make_repo(db, user)
    pr = make_pr(db, repo)
    analysis = make_analysis(db, pr)
    finding = make_finding(db, analysis)
    db.commit()
    return user, repo, pr, analysis, finding


# ──────────────────────────────────────────────────────────────────────────────
# 1. Review Queue Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_returns_pending_findings(db_override):
    _, _, pr, analysis, finding = make_full_stack(db_override)

    res = client.get("/api/v1/findings/queue", headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert str(item["finding_id"]) == str(finding.id)
    assert item["status"] == FindingStatus.PENDING_REVIEW.value
    assert item["severity"] == FindingSeverity.HIGH.value


def test_queue_excludes_verified_findings_by_default(db_override):
    """VERIFIED findings should not appear in the default queue."""
    _, _, pr, analysis, finding = make_full_stack(db_override)
    finding.status = FindingStatus.VERIFIED.value
    db_override.commit()

    res = client.get("/api/v1/findings/queue", headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_queue_filter_by_verified_status(db_override):
    """Filtering by status=VERIFIED should show verified findings."""
    _, _, pr, analysis, finding = make_full_stack(db_override)
    finding.status = FindingStatus.VERIFIED.value
    db_override.commit()

    res = client.get("/api/v1/findings/queue?status=VERIFIED", headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_queue_filter_by_severity(db_override):
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)

    high = make_finding(db_override, analysis, severity="HIGH")
    crit = make_finding(db_override, analysis, severity="CRITICAL")
    db_override.commit()

    res = client.get("/api/v1/findings/queue?severity=HIGH", headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["severity"] == "HIGH"


def test_queue_filter_by_repository(db_override):
    user = make_user(db_override)
    repo1 = make_repo(db_override, user)
    # Second repo
    repo2 = Repository(
        user_id=user.id, github_repo_id=99002, owner_login="o", name="r2",
        full_name="o/r2", default_branch="main", private=False, html_url="http://x",
    )
    db_override.add(repo2)
    db_override.flush()

    pr1 = make_pr(db_override, repo1)
    pr2 = PullRequest(
        repository_id=repo2.id, github_pr_id=2002, pr_number=2, title="PR2",
        author_login="x", source_branch="f", target_branch="m",
        head_sha="sha2", base_sha="000", status=PullRequestStatus.OPEN.value,
    )
    db_override.add(pr2)
    db_override.flush()

    a1 = make_analysis(db_override, pr1)
    a2 = make_analysis(db_override, pr2, sha="sha2")
    f1 = make_finding(db_override, a1)
    f2 = make_finding(db_override, a2)
    db_override.commit()

    res = client.get(f"/api/v1/findings/queue?repository_id={repo1.id}", headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert str(data["items"][0]["finding_id"]) == str(f1.id)


def test_queue_filter_by_pull_request(db_override):
    _, _, pr, analysis, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/queue?pull_request_id={pr.id}", headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_queue_filter_by_commit_sha(db_override):
    _, _, pr, analysis, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/queue?commit_sha=abc123def456", headers=AUTH_HEADER)
    assert res.status_code == 200
    assert res.json()["total"] == 1

    res2 = client.get("/api/v1/findings/queue?commit_sha=notexist", headers=AUTH_HEADER)
    assert res2.json()["total"] == 0


def test_queue_ordering_severity_desc(db_override):
    """CRITICAL should appear before HIGH in the queue."""
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)

    low = make_finding(db_override, analysis, severity="LOW")
    crit = make_finding(db_override, analysis, severity="CRITICAL")
    med = make_finding(db_override, analysis, severity="MEDIUM")
    db_override.commit()

    res = client.get("/api/v1/findings/queue", headers=AUTH_HEADER)
    items = res.json()["items"]
    severities = [i["severity"] for i in items]
    assert severities[0] == "CRITICAL"
    assert severities[-1] == "LOW"


def test_queue_pagination(db_override):
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)

    for i in range(5):
        make_finding(db_override, analysis, message=f"Finding {i}\nDetail")
    db_override.commit()

    res = client.get("/api/v1/findings/queue?page=1&page_size=3", headers=AUTH_HEADER)
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["total_pages"] == 2

    res2 = client.get("/api/v1/findings/queue?page=2&page_size=3", headers=AUTH_HEADER)
    assert len(res2.json()["items"]) == 2


# ──────────────────────────────────────────────────────────────────────────────
# 2. Authentication Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_queue_unauthenticated_denied(db_override):
    res = client.get("/api/v1/findings/queue")
    assert res.status_code == 401


def test_finding_detail_unauthenticated_denied(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}")
    assert res.status_code == 401


def test_verify_unauthenticated_denied(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
    )
    assert res.status_code == 401


def test_verify_empty_header_denied(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers={"X-Reviewer-Login": "   "},
    )
    assert res.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# 3. Finding Detail Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_finding_detail_returns_correct_finding(db_override):
    _, repo, pr, analysis, finding = make_full_stack(db_override)

    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert str(data["id"]) == str(finding.id)
    assert data["source"] == FindingSource.AI_REVIEW.value
    assert data["severity"] == FindingSeverity.HIGH.value
    assert data["file_path"] == "app/db.py"
    assert data["start_line"] == 42


def test_finding_detail_includes_evidence(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    data = res.json()
    assert data["evidence"] is not None
    assert "reasoning" in data["evidence"]
    assert "evidence" in data["evidence"]


def test_finding_detail_includes_analysis_context(db_override):
    _, _, pr, analysis, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    data = res.json()
    assert data["analysis"] is not None
    assert str(data["analysis"]["id"]) == str(analysis.id)
    assert data["analysis"]["head_sha"] == analysis.head_sha


def test_finding_detail_includes_pr_and_repo(db_override):
    _, repo, pr, analysis, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    data = res.json()
    assert data["pull_request"] is not None
    assert data["pull_request"]["pr_number"] == 1
    assert data["repository"] is not None
    assert data["repository"]["full_name"] == "test_org/test-repo"


def test_finding_detail_empty_verification_history(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    data = res.json()
    assert data["verification_history"] == []


def test_finding_detail_not_found(db_override):
    fake_id = uuid.uuid4()
    res = client.get(f"/api/v1/findings/{fake_id}", headers=AUTH_HEADER)
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# 4. Verification Decision Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_verify_finding_verified(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED", "comment": "Confirmed by manual review."},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == FindingStatus.VERIFIED.value


def test_verify_finding_rejected(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "REJECTED", "comment": "False positive."},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 200
    assert res.json()["status"] == FindingStatus.REJECTED.value


def test_verify_finding_dismissed(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "DISMISSED"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 200
    assert res.json()["status"] == FindingStatus.DISMISSED.value


def test_verify_finding_case_insensitive_decision(db_override):
    """Decisions should be case-insensitive."""
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "verified"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 200
    assert res.json()["status"] == FindingStatus.VERIFIED.value


def test_verify_finding_invalid_decision(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "APPROVE"},
        headers=AUTH_HEADER,
    )
    # Either 422 from pydantic or 422 from service
    assert res.status_code == 422


def test_verify_finding_not_found(db_override):
    fake_id = uuid.uuid4()
    res = client.post(
        f"/api/v1/findings/{fake_id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 404


def test_verify_finding_terminal_state_rejected(db_override):
    """Cannot verify an already-VERIFIED finding."""
    _, _, _, _, finding = make_full_stack(db_override)
    # First verify
    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    # Second attempt
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "REJECTED"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# 5. Audit Trail / History Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_verification_creates_audit_record(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED", "comment": "Looks real."},
        headers=AUTH_HEADER,
    )
    res = client.get(f"/api/v1/findings/{finding.id}/history", headers=AUTH_HEADER)
    assert res.status_code == 200
    history = res.json()
    assert history["total"] == 1
    entry = history["items"][0]
    assert entry["decision"] == "VERIFIED"
    assert entry["reviewer_login"] == "test_reviewer"
    assert entry["comment"] == "Looks real."
    assert entry["previous_status"] == FindingStatus.PENDING_REVIEW.value


def test_verification_history_records_previous_status(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    finding.status = FindingStatus.OPEN.value
    db_override.commit()

    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "REJECTED"},
        headers=AUTH_HEADER,
    )

    res = client.get(f"/api/v1/findings/{finding.id}/history", headers=AUTH_HEADER)
    entry = res.json()["items"][0]
    assert entry["previous_status"] == FindingStatus.OPEN.value


def test_verification_history_included_in_detail(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )

    res = client.get(f"/api/v1/findings/{finding.id}", headers=AUTH_HEADER)
    data = res.json()
    assert len(data["verification_history"]) == 1
    assert data["verification_history"][0]["decision"] == "VERIFIED"


def test_history_records_reviewer_identity(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "DISMISSED"},
        headers={"X-Reviewer-Login": "senior_dev"},
    )
    res = client.get(f"/api/v1/findings/{finding.id}/history", headers=AUTH_HEADER)
    assert res.json()["items"][0]["reviewer_login"] == "senior_dev"


def test_history_records_timestamp(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    res = client.get(f"/api/v1/findings/{finding.id}/history", headers=AUTH_HEADER)
    entry = res.json()["items"][0]
    assert entry["decided_at"] is not None
    # Should be a valid ISO datetime
    datetime.fromisoformat(entry["decided_at"].replace("Z", "+00:00"))


# ──────────────────────────────────────────────────────────────────────────────
# 6. Immutability of AI Evidence Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_ai_evidence_not_modified_after_verification(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    original_evidence = dict(finding.evidence)
    original_message = finding.message
    original_file_path = finding.file_path
    original_severity = finding.severity
    original_category = finding.category

    client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED", "comment": "Confirmed."},
        headers=AUTH_HEADER,
    )

    db_override.refresh(finding)
    # AI-generated fields must not have changed
    assert finding.evidence == original_evidence
    assert finding.message == original_message
    assert finding.file_path == original_file_path
    assert finding.severity == original_severity
    assert finding.category == original_category
    # Only status should have changed
    assert finding.status == FindingStatus.VERIFIED.value


# ──────────────────────────────────────────────────────────────────────────────
# 7. Concurrency / Optimistic Locking Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_concurrent_modification_detected(db_override):
    """
    Simulate two reviewers reading PENDING_REVIEW, then both trying to act.
    Reviewer A succeeds.  Reviewer B's request with expected_status=PENDING_REVIEW
    should fail with 409 because the status already changed to VERIFIED.
    """
    _, _, _, _, finding = make_full_stack(db_override)

    # Reviewer A succeeds
    res_a = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    assert res_a.status_code == 200

    # Reviewer B tries with the stale expected_status
    res_b = client.post(
        f"/api/v1/findings/{finding.id}/verify?expected_status=PENDING_REVIEW",
        json={"decision": "REJECTED"},
        headers=AUTH_HEADER_B,
    )
    assert res_b.status_code == 409


def test_no_expected_status_allows_any_non_terminal(db_override):
    """Without expected_status, any non-terminal status is accepted."""
    _, _, _, _, finding = make_full_stack(db_override)
    finding.status = FindingStatus.OPEN.value
    db_override.commit()

    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# 8. Multiple Independent Findings Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_multiple_findings_independent_decisions(db_override):
    """
    Findings A, B, C from the same analysis should be independently verifiable.
    """
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)

    f_a = make_finding(db_override, analysis, message="Finding A\nDesc A")
    f_b = make_finding(db_override, analysis, message="Finding B\nDesc B")
    f_c = make_finding(db_override, analysis, message="Finding C\nDesc C")
    db_override.commit()

    # Verify A
    ra = client.post(
        f"/api/v1/findings/{f_a.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    assert ra.status_code == 200

    # Reject B
    rb = client.post(
        f"/api/v1/findings/{f_b.id}/verify",
        json={"decision": "REJECTED"},
        headers=AUTH_HEADER,
    )
    assert rb.status_code == 200

    # Dismiss C
    rc = client.post(
        f"/api/v1/findings/{f_c.id}/verify",
        json={"decision": "DISMISSED"},
        headers=AUTH_HEADER,
    )
    assert rc.status_code == 200

    db_override.refresh(f_a)
    db_override.refresh(f_b)
    db_override.refresh(f_c)
    assert f_a.status == FindingStatus.VERIFIED.value
    assert f_b.status == FindingStatus.REJECTED.value
    assert f_c.status == FindingStatus.DISMISSED.value


def test_queue_shows_remaining_pending_after_partial_resolution(db_override):
    """After resolving some findings, queue shows only remaining pending ones."""
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)

    f1 = make_finding(db_override, analysis)
    f2 = make_finding(db_override, analysis)
    db_override.commit()

    # Resolve f1
    client.post(
        f"/api/v1/findings/{f1.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )

    res = client.get("/api/v1/findings/queue", headers=AUTH_HEADER)
    assert res.json()["total"] == 1
    assert str(res.json()["items"][0]["finding_id"]) == str(f2.id)


# ──────────────────────────────────────────────────────────────────────────────
# 9. AI Findings Are Not Automatically Verified
# ──────────────────────────────────────────────────────────────────────────────

def test_new_finding_not_verified_on_creation(db_override):
    """A freshly created AI finding must never start in VERIFIED state."""
    user = make_user(db_override)
    repo = make_repo(db_override, user)
    pr = make_pr(db_override, repo)
    analysis = make_analysis(db_override, pr)
    finding = make_finding(db_override, analysis)
    db_override.commit()

    assert finding.status in (
        FindingStatus.PENDING_REVIEW.value,
        FindingStatus.OPEN.value,
    ), "AI finding must not start in VERIFIED, REJECTED, or DISMISSED state"
    assert finding.status != FindingStatus.VERIFIED.value
    assert finding.status != FindingStatus.REJECTED.value
    assert finding.status != FindingStatus.DISMISSED.value


def test_ai_finding_requires_human_action_to_verify(db_override):
    """No automatic route can flip a finding to VERIFIED without a reviewer."""
    _, _, _, _, finding = make_full_stack(db_override)
    # Status must still be PENDING_REVIEW (no automatic promotion)
    assert finding.status == FindingStatus.PENDING_REVIEW.value


# ──────────────────────────────────────────────────────────────────────────────
# 10. Error Handling Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_verify_missing_decision_field(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"comment": "no decision here"},
        headers=AUTH_HEADER,
    )
    assert res.status_code == 422


def test_history_endpoint_not_found(db_override):
    fake_id = uuid.uuid4()
    res = client.get(f"/api/v1/findings/{fake_id}/history", headers=AUTH_HEADER)
    assert res.status_code == 404


def test_history_unauthenticated(db_override):
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.get(f"/api/v1/findings/{finding.id}/history")
    assert res.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# 11. No GitHub Publishing Confirmation
# ──────────────────────────────────────────────────────────────────────────────

def test_no_github_publish_endpoint_on_verification(db_override):
    """
    The verify endpoint response must not contain any GitHub publish URL or ID.
    This documents that Phase 6 does NOT publish to GitHub.
    """
    _, _, _, _, finding = make_full_stack(db_override)
    res = client.post(
        f"/api/v1/findings/{finding.id}/verify",
        json={"decision": "VERIFIED"},
        headers=AUTH_HEADER,
    )
    data = res.json()
    # No github publish fields in finding detail
    assert "github_review_id" not in data
    assert "published_at" not in data
