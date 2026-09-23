import uuid
from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

import app.core.security as security
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app
from app.models.analysis import Analysis, AnalysisStatus, AnalysisTrigger
from app.models.commit import Commit
from app.models.commit_analysis import CommitAnalysisStatus
from app.models.finding import Finding, FindingCategory, FindingSeverity, FindingSource, FindingStatus
from app.models.pull_request import PullRequest, PullRequestStatus
from app.models.repository import Repository
from app.models.review import Review, ReviewStatus
from app.models.user import User

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Vigil backend is running", "version": "1.0.0"}


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"


def test_me_requires_auth():
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_malformed_authorization_header_is_rejected():
    response = client.get("/api/v1/me", headers={"Authorization": "Token abc123"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_invalid_jwt_is_rejected(monkeypatch):
    def fake_validate(token: str):
        raise ValueError("invalid token")

    monkeypatch.setattr("app.core.security.validate_access_token", fake_validate)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_expired_token_is_rejected(monkeypatch):
    class DummyKey:
        algorithm_name = "RS256"
        key = "secret"

    monkeypatch.setattr(security, "_get_signing_key", lambda token: DummyKey())

    def fake_decode(*args, **kwargs):
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(security.jwt, "decode", fake_decode)
    with pytest.raises(ValueError, match="Token expired"):
        security.validate_access_token("expired-token")


def test_wrong_issuer_is_rejected(monkeypatch):
    class DummyKey:
        algorithm_name = "RS256"
        key = "secret"

    monkeypatch.setattr(security, "_get_signing_key", lambda token: DummyKey())

    def fake_decode(*args, **kwargs):
        raise jwt.InvalidTokenError("wrong issuer")

    monkeypatch.setattr(security.jwt, "decode", fake_decode)
    with pytest.raises(ValueError, match="Invalid token"):
        security.validate_access_token("issuer-token")


def test_wrong_audience_is_rejected(monkeypatch):
    class DummyKey:
        algorithm_name = "RS256"
        key = "secret"

    monkeypatch.setattr(security, "_get_signing_key", lambda token: DummyKey())

    def fake_decode(*args, **kwargs):
        raise jwt.InvalidAudienceError("wrong audience")

    monkeypatch.setattr(security.jwt, "decode", fake_decode)
    with pytest.raises(ValueError, match="Invalid token"):
        security.validate_access_token("audience-token")


def test_missing_scope_is_forbidden(monkeypatch):
    def fake_validate(token: str):
        raise PermissionError("insufficient permissions")

    monkeypatch.setattr("app.core.security.validate_access_token", fake_validate)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer access-token-without-scope"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_valid_entra_token_returns_authenticated_user(monkeypatch):
    def fake_validate(token: str):
        return {
            "oid": "user-123",
            "preferred_username": "user@example.com",
            "name": "Example User",
            "tid": "tenant-123",
            "scp": "access_as_user",
        }

    monkeypatch.setattr("app.core.security.validate_access_token", fake_validate)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["oid"] == "user-123"
    assert payload["user"]["scopes"] == ["access_as_user"]


def test_list_repositories():
    res = client.get("/api/v1/repositories")
    assert res.status_code == 200
    assert "items" in res.json()


def test_get_repository_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/repositories/{fake_id}")
    assert res.status_code == 404


def test_get_pull_request_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/pull-requests/{fake_id}")
    assert res.status_code == 404


def test_get_analysis_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/analyses/{fake_id}")
    assert res.status_code == 404


def test_get_commit_not_found():
    res = client.get("/api/v1/commits/nonexistent_sha_999")
    assert res.status_code == 404


def test_get_findings_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/pull-requests/{fake_id}/findings")
    assert res.status_code == 404


def test_get_review_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/pull-requests/{fake_id}/review")
    assert res.status_code == 404


def test_publish_review_not_implemented():
    fake_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/reviews/{fake_id}/publish")
    assert res.status_code == 501


def test_get_review_queue_not_found():
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/review-queue/{fake_id}")
    assert res.status_code == 404
