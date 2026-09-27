import hashlib
import hmac
from typing import Optional

from app.core.config import settings
from app.integrations.github.exceptions import GitHubInvalidSignatureException


def verify_github_signature(
    raw_payload_bytes: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """
    Verify incoming GitHub webhook request signature (X-Hub-Signature-256).

    GitHub signs the exact raw request body using HMAC-SHA256 with the configured secret.
    This function computes the expected HMAC digest and uses constant-time comparison.
    """
    webhook_secret = secret or settings.GITHUB_WEBHOOK_SECRET
    if not webhook_secret:
        raise GitHubInvalidSignatureException(
            "GITHUB_WEBHOOK_SECRET is not configured on the server."
        )

    if not signature_header:
        raise GitHubInvalidSignatureException("Missing X-Hub-Signature-256 header.")

    if not signature_header.startswith("sha256="):
        raise GitHubInvalidSignatureException(
            "Invalid X-Hub-Signature-256 header format. Expected 'sha256=<hex_digest>'."
        )

    secret_bytes = webhook_secret.encode("utf-8")
    computed_digest = hmac.new(
        secret_bytes,
        msg=raw_payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    expected_signature = f"sha256={computed_digest}"

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature_header):
        raise GitHubInvalidSignatureException("GitHub webhook signature verification failed.")

    return True
