import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import httpx

from app.integrations.github.auth import GitHubAuthManager
from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import (
    GitHubAPIException,
    GitHubAuthenticationException,
    GitHubInstallationNotFoundException,
    GitHubPermissionDeniedException,
    GitHubRateLimitException,
    GitHubResourceNotFoundException,
    GitHubValidationErrorException,
)


@pytest.fixture
def generate_rsa_key_pem():
    """Generate a test RSA 2048 private key in PEM format for unit tests."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


# ============================================================================
# 1. JWT TESTS
# ============================================================================

def test_jwt_generation_success(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)

    token = auth_mgr.generate_app_jwt()
    assert token is not None
    assert isinstance(token, str)

    # Decode and verify claims without verifying signature
    unverified_payload = jwt.decode(token, options={"verify_signature": False})
    assert unverified_payload["iss"] == "123456"

    # Verify iat and exp
    now = int(time.time())
    assert unverified_payload["iat"] <= now
    assert unverified_payload["exp"] > now
    # Max expiration should be ~10 minutes (600s + 60s leeway)
    assert unverified_payload["exp"] - unverified_payload["iat"] == 660


def test_jwt_generation_missing_app_id(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="", private_key=pem_key)

    with pytest.raises(GitHubAuthenticationException) as exc_info:
        auth_mgr.generate_app_jwt()
    assert "GITHUB_APP_ID is not configured" in str(exc_info.value)


def test_jwt_generation_invalid_private_key():
    auth_mgr = GitHubAuthManager(app_id="123456", private_key="INVALID_PEM_KEY")

    with pytest.raises(GitHubAuthenticationException) as exc_info:
        auth_mgr.generate_app_jwt()
    assert "Failed to sign GitHub App JWT" in str(exc_info.value)


# ============================================================================
# 2. INSTALLATION ACCESS TOKEN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_installation_token_success(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "token": "ghs_mock_installation_token_12345",
        "expires_at": "2030-01-01T00:00:00Z",
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    token = await auth_mgr.get_installation_token(installation_id=98765, client=mock_client)

    assert token == "ghs_mock_installation_token_12345"
    mock_client.post.assert_called_once()

    # Repeated call should hit in-memory cache and not make a second HTTP request
    cached_token = await auth_mgr.get_installation_token(installation_id=98765, client=mock_client)
    assert cached_token == "ghs_mock_installation_token_12345"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_get_installation_token_401_auth_failure(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    with pytest.raises(GitHubAuthenticationException):
        await auth_mgr.get_installation_token(installation_id=98765, client=mock_client)


@pytest.mark.asyncio
async def test_get_installation_token_404_invalid_installation(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    with pytest.raises(GitHubInstallationNotFoundException):
        await auth_mgr.get_installation_token(installation_id=99999, client=mock_client)


# ============================================================================
# 3. GITHUB API CLIENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_client_request_success(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    with patch.object(auth_mgr, "get_installation_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = "ghs_mock_token"

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 100, "name": "test-repo"}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            res = await client.request("GET", "/repos/owner/test-repo", installation_id=98765)

            assert res == {"id": 100, "name": "test-repo"}
            mock_get_token.assert_called_once_with(98765, client=pytest.any_int if False else unittest_mock_anything())


def unittest_mock_anything():
    class Anything:
        def __eq__(self, other):
            return True
    return Anything()


@pytest.mark.asyncio
async def test_client_request_401_raises_auth_exception(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubAuthenticationException):
            await client.request("GET", "/user")


@pytest.mark.asyncio
async def test_client_request_403_rate_limit(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}
    mock_response.text = "API rate limit exceeded"

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubRateLimitException) as exc_info:
            await client.request("GET", "/repos")
        assert exc_info.value.retry_after == 1700000000


@pytest.mark.asyncio
async def test_client_request_404_not_found(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubResourceNotFoundException):
            await client.request("GET", "/repos/nonexistent/repo")


@pytest.mark.asyncio
async def test_client_request_422_validation_error(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "Validation Failed", "errors": []}

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(GitHubValidationErrorException):
            await client.request("POST", "/repos/owner/repo/pulls")


@pytest.mark.asyncio
async def test_client_request_timeout(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    with patch("httpx.AsyncClient.request", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(GitHubAPIException) as exc_info:
            await client.request("GET", "/repos")
        assert exc_info.value.status_code == 504


# ============================================================================
# 4. REPOSITORY RETRIEVAL & PAGINATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_installation_repositories_single_page(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    mock_data = {
        "total_count": 2,
        "repositories": [
            {"id": 1, "name": "repo1", "full_name": "owner/repo1"},
            {"id": 2, "name": "repo2", "full_name": "owner/repo2"},
        ],
    }

    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_data

        res = await client.get_installation_repositories(installation_id=123, page=1, per_page=30)
        assert res["total_count"] == 2
        assert len(res["repositories"]) == 2
        mock_req.assert_called_once_with(
            method="GET",
            endpoint="/installation/repositories",
            installation_id=123,
            params={"page": 1, "per_page": 30},
        )


@pytest.mark.asyncio
async def test_get_all_installation_repositories_pagination(generate_rsa_key_pem):
    pem_key = generate_rsa_key_pem
    auth_mgr = GitHubAuthManager(app_id="123456", private_key=pem_key)
    client = GitHubClient(auth_manager=auth_mgr)

    page1 = {
        "total_count": 3,
        "repositories": [
            {"id": 1, "name": "repo1"},
            {"id": 2, "name": "repo2"},
        ],
    }
    page2 = {
        "total_count": 3,
        "repositories": [
            {"id": 3, "name": "repo3"},
        ],
    }

    with patch.object(client, "get_installation_repositories", new_callable=AsyncMock) as mock_get_repos:
        mock_get_repos.side_effect = [page1, page2]

        all_repos = await client.get_all_installation_repositories(installation_id=123, per_page=2)

        assert len(all_repos) == 3
        assert [r["id"] for r in all_repos] == [1, 2, 3]
        assert mock_get_repos.call_count == 2
