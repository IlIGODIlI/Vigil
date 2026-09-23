import json
from typing import Any
from urllib.request import urlopen

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)
REQUIRED_SCOPE = "access_as_user"


def _get_oidc_config() -> dict[str, Any]:
    issuer = f"https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/v2.0"
    config_url = f"{issuer}/.well-known/openid-configuration"
    with urlopen(config_url) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_jwks() -> dict[str, Any]:
    oidc_config = _get_oidc_config()
    jwks_url = oidc_config.get("jwks_uri")
    if not jwks_url:
        raise ValueError("Unable to load Microsoft Entra JWKS configuration")
    with urlopen(jwks_url) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_signing_key(token: str) -> jwt.PyJWK:
    try:
        unverified = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid token format") from exc

    kid = unverified.get("kid")
    if not kid:
        raise ValueError("Token missing key identifier")

    jwks = _get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.PyJWK.from_dict(key)

    raise ValueError("Signing key not found")


def validate_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise ValueError("Missing token")

    signing_key = _get_signing_key(token)
    issuer = f"https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/v2.0"
    expected_audience = settings.ENTRA_API_CLIENT_ID

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=expected_audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "scp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc

    scopes = claims.get("scp")
    if isinstance(scopes, str):
        scope_values = {scope.strip() for scope in scopes.split(" ") if scope.strip()}
    else:
        scope_values = set()

    if REQUIRED_SCOPE not in scope_values:
        raise PermissionError("insufficient permissions")

    return claims


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = credentials.credentials

    try:
        claims = validate_access_token(token)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required") from exc

    scopes = claims.get("scp")
    if isinstance(scopes, str):
        scope_values = [scope for scope in scopes.split(" ") if scope.strip()]
    else:
        scope_values = []

    user = {
        "oid": claims.get("oid") or claims.get("sub"),
        "preferred_username": claims.get("preferred_username"),
        "name": claims.get("name"),
        "tenant_id": claims.get("tid") or settings.ENTRA_TENANT_ID,
        "scopes": scope_values,
    }
    return user
