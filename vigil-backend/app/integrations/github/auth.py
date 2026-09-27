from datetime import datetime, timezone, timedelta
import os
import time
from typing import Dict, Optional, Tuple

import httpx
import jwt

from app.core.config import settings
from app.integrations.github.exceptions import (
    GitHubAPIException,
    GitHubAuthenticationException,
    GitHubInstallationNotFoundException,
    GitHubPermissionDeniedException,
    GitHubRateLimitException,
)


class GitHubAuthManager:
    """Manages GitHub App authentication, JWT generation, and installation access token retrieval."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        self._app_id = app_id
        self._private_key = private_key
        self._private_key_path = private_key_path
        self._api_base_url = api_base_url
        self._token_cache: Dict[int, Tuple[str, datetime]] = {}

    @property
    def app_id(self) -> str:
        return self._app_id or settings.GITHUB_APP_ID

    @property
    def private_key(self) -> str:
        return self._private_key or settings.GITHUB_PRIVATE_KEY

    @property
    def private_key_path(self) -> str:
        return self._private_key_path or settings.GITHUB_PRIVATE_KEY_PATH

    @property
    def api_base_url(self) -> str:
        return self._api_base_url or settings.GITHUB_API_BASE_URL or "https://api.github.com"

    def _get_pem_private_key(self) -> str:
        key = self.private_key
        if key:
            # Handle env vars formatted with literal escaped newlines "\n"
            if "\\n" in key:
                key = key.replace("\\n", "\n")
            return key.strip()

        path = self.private_key_path
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                raise GitHubAuthenticationException(
                    f"Failed to read GitHub App private key file: {str(e)}"
                ) from e

        raise GitHubAuthenticationException(
            "GitHub App private key is not configured. Provide GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH."
        )

    def generate_app_jwt(self) -> str:
        """Generate a signed RS256 JWT for GitHub App authentication."""
        app_id = self.app_id
        if not app_id:
            raise GitHubAuthenticationException("GITHUB_APP_ID is not configured.")

        pem_key = self._get_pem_private_key()

        now = int(time.time())
        payload = {
            "iat": now - 60,  # 60 seconds clock drift leeway
            "exp": now + (10 * 60),  # 10 minutes max expiration allowed by GitHub
            "iss": str(app_id),
        }

        try:
            token = jwt.encode(payload, pem_key, algorithm="RS256")
            if isinstance(token, bytes):
                return token.decode("utf-8")
            return token
        except Exception as e:
            raise GitHubAuthenticationException(
                f"Failed to sign GitHub App JWT: {str(e)}"
            ) from e

    async def get_installation_token(
        self,
        installation_id: int,
        client: Optional[httpx.AsyncClient] = None,
    ) -> str:
        """Obtain an installation access token for a specific installation ID with safe caching."""
        now_utc = datetime.now(timezone.utc)

        # Check in-memory cache with a 60-second safety buffer
        if installation_id in self._token_cache:
            cached_token, expires_at = self._token_cache[installation_id]
            if now_utc + timedelta(seconds=60) < expires_at:
                return cached_token

        jwt_token = self.generate_app_jwt()
        url = f"{self.api_base_url.rstrip('/')}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Vigil-App",
        }

        close_client_after = False
        if client is None:
            client = httpx.AsyncClient(timeout=30.0)
            close_client_after = True

        try:
            response = await client.post(url, headers=headers)
        except httpx.TimeoutException as e:
            raise GitHubAPIException(
                "Timeout connecting to GitHub API for installation token", status_code=504
            ) from e
        except httpx.NetworkError as e:
            raise GitHubAPIException(
                "Network error connecting to GitHub API for installation token", status_code=502
            ) from e
        finally:
            if close_client_after:
                await client.aclose()

        if response.status_code in (200, 201):
            data = response.json()
            token = data.get("token")
            expires_at_str = data.get("expires_at")
            if not token:
                raise GitHubAPIException(
                    "Invalid response from GitHub API: missing installation token"
                )

            # Parse expires_at (ISO 8601 string)
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                except ValueError:
                    expires_at = now_utc + timedelta(hours=1)
            else:
                expires_at = now_utc + timedelta(hours=1)

            self._token_cache[installation_id] = (token, expires_at)
            return token

        elif response.status_code == 401:
            raise GitHubAuthenticationException(
                "GitHub App authentication failed when requesting installation token"
            )
        elif response.status_code == 403:
            raise GitHubPermissionDeniedException(
                f"Permission denied for installation ID {installation_id}"
            )
        elif response.status_code == 404:
            raise GitHubInstallationNotFoundException(
                f"GitHub Installation ID {installation_id} not found"
            )
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise GitHubRateLimitException(
                "GitHub API rate limit exceeded during installation token request",
                retry_after=retry_seconds,
            )
        else:
            raise GitHubAPIException(
                f"Unexpected error from GitHub API ({response.status_code})",
                status_code=502,
            )
