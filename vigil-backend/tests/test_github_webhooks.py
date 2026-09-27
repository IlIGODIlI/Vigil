import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.integrations.github.webhooks.security import verify_github_signature
from app.integrations.github.webhooks.tracker import webhook_delivery_tracker
from app.integrations.github.webhooks.schemas import normalize_webhook_payload
from app.integrations.github.exceptions import GitHubInvalidSignatureException

client = TestClient(app)


def compute_signature(secret: str, body_bytes: bytes) -> str:
    """Compute HMAC-SHA256 signature for test payload."""
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture(autouse=True)
def reset_tracker():
    """Clear delivery tracker cache before each test."""
    webhook_delivery_tracker.clear()


# ============================================================================
# 1. SIGNATURE VERIFICATION TESTS
# ============================================================================

def test_signature_verification_success():
    secret = "test_secret_key"
    payload = b'{"hello": "world"}'
    sig = compute_signature(secret, payload)

    assert verify_github_signature(payload, sig, secret=secret) is True


def test_signature_verification_invalid():
    secret = "test_secret_key"
    payload = b'{"hello": "world"}'
    invalid_sig = "sha256=invalid_hex_digest_0000000000000000000000000000000000000000"

    with pytest.raises(GitHubInvalidSignatureException):
        verify_github_signature(payload, invalid_sig, secret=secret)


def test_signature_verification_missing_header():
    with pytest.raises(GitHubInvalidSignatureException):
        verify_github_signature(b"{}", None, secret="secret")


def test_signature_verification_malformed_header():
    with pytest.raises(GitHubInvalidSignatureException):
        verify_github_signature(b"{}", "invalid_prefix_without_sha256", secret="secret")


# ============================================================================
# 2. FASTAPI ENDPOINT SIGNATURE & HEADER TESTS
# ============================================================================

def test_webhook_endpoint_missing_signature():
    secret = settings.GITHUB_WEBHOOK_SECRET or "test_secret"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    try:
        response = client.post(
            "/api/v1/webhooks/github",
            json={"test": "data"},
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "delivery-1"},
        )
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


def test_webhook_endpoint_invalid_signature():
    secret = settings.GITHUB_WEBHOOK_SECRET or "test_secret"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    try:
        response = client.post(
            "/api/v1/webhooks/github",
            json={"test": "data"},
            headers={
                "X-Hub-Signature-256": "sha256=badsignature",
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-1",
            },
        )
        assert response.status_code == 401
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


def test_webhook_endpoint_missing_event_header():
    secret = settings.GITHUB_WEBHOOK_SECRET or "test_secret"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    try:
        body = json.dumps({"test": "data"}).encode("utf-8")
        sig = compute_signature(secret, body)

        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Delivery": "delivery-1",
            },
        )
        assert response.status_code == 400
        assert "Missing X-GitHub-Event header" in response.json()["detail"]
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


def test_webhook_endpoint_missing_delivery_header():
    secret = settings.GITHUB_WEBHOOK_SECRET or "test_secret"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    try:
        body = json.dumps({"test": "data"}).encode("utf-8")
        sig = compute_signature(secret, body)

        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "push",
            },
        )
        assert response.status_code == 400
        assert "Missing X-GitHub-Delivery header" in response.json()["detail"]
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


# ============================================================================
# 3. PUSH EVENT PROCESSING
# ============================================================================

def test_webhook_push_event():
    secret = "webhook_secret_123"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    payload = {
        "installation": {"id": 999111},
        "ref": "refs/heads/main",
        "before": "0000000000000000000000000000000000000000",
        "after": "1111111111111111111111111111111111111111",
        "repository": {
            "id": 12345,
            "name": "vigil-repo",
            "full_name": "vigil-org/vigil-repo",
            "owner": {"login": "vigil-org"},
            "private": True,
            "html_url": "https://github.com/vigil-org/vigil-repo",
            "default_branch": "main",
        },
        "commits": [
            {
                "id": "1111111111111111111111111111111111111111",
                "message": "feat: initial commit",
                "timestamp": "2026-09-26T12:00:00Z",
                "author": {"name": "Developer", "email": "dev@example.com"},
            }
        ],
        "sender": {"id": 42, "login": "octocat"},
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        sig = compute_signature(secret, body)

        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-push-100",
            },
        )
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "processed"
        assert res_data["event_type"] == "push"
        assert res_data["repository"] == "vigil-org/vigil-repo"
        assert res_data["ref"] == "refs/heads/main"
        assert res_data["commits_count"] == 1
        assert res_data["installation_id"] == 999111
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


# ============================================================================
# 4. PULL REQUEST EVENT PROCESSING (opened, synchronize, reopened, closed)
# ============================================================================

@pytest.mark.parametrize("action", ["opened", "synchronize", "reopened", "closed"])
def test_webhook_pull_request_events(action):
    secret = "webhook_secret_123"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    payload = {
        "action": action,
        "number": 15,
        "installation": {"id": 888222},
        "repository": {
            "id": 12345,
            "name": "vigil-repo",
            "full_name": "vigil-org/vigil-repo",
            "owner": {"login": "vigil-org"},
            "private": False,
            "html_url": "https://github.com/vigil-org/vigil-repo",
        },
        "pull_request": {
            "id": 999,
            "number": 15,
            "title": "Add feature X",
            "body": "PR description",
            "state": "closed" if action == "closed" else "open",
            "merged": True if action == "closed" else False,
            "head": {"sha": "head_sha_abc", "ref": "feature-x"},
            "base": {"sha": "base_sha_xyz", "ref": "main"},
            "user": {"login": "contributor"},
        },
        "sender": {"id": 100, "login": "contributor"},
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        sig = compute_signature(secret, body)
        delivery_id = f"delivery-pr-{action}-101"

        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
            },
        )
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "processed"
        assert res_data["event_type"] == "pull_request"
        assert res_data["action"] == action
        assert res_data["pr_number"] == 15
        assert res_data["repository"] == "vigil-org/vigil-repo"
        assert res_data["head_sha"] == "head_sha_abc"
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


# ============================================================================
# 5. IDEMPOTENCY / DUPLICATE DELIVERY TESTS
# ============================================================================

def test_webhook_idempotency_duplicate_delivery():
    secret = "webhook_secret_123"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    payload = {
        "ref": "refs/heads/main",
        "repository": {"id": 1, "name": "r", "full_name": "o/r", "owner": {"login": "o"}, "html_url": "u"},
        "sender": {"id": 1, "login": "u"},
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        sig = compute_signature(secret, body)
        delivery_id = "duplicate-delivery-test-99"

        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
        }

        # First delivery -> Processed
        resp1 = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        # Second delivery with SAME delivery_id -> Duplicate
        resp2 = client.post("/api/v1/webhooks/github", content=body, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"
        assert resp2.json()["message"] == "Delivery already processed"
        assert resp2.json()["delivery_id"] == delivery_id
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret


# ============================================================================
# 6. UNSUPPORTED EVENT TESTS
# ============================================================================

def test_webhook_unsupported_event():
    secret = "webhook_secret_123"
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = secret

    payload = {"action": "created", "issue": {"id": 1}}

    try:
        body = json.dumps(payload).encode("utf-8")
        sig = compute_signature(secret, body)

        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "delivery-unsupported-1",
            },
        )
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "ignored"
        assert "Unsupported event type: 'issues'" in res_data["reason"]
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret
