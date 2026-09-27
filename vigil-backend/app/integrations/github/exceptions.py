from typing import Optional
from app.core.exceptions import VigilException


class GitHubIntegrationException(VigilException):
    """Base exception for all GitHub integration errors."""

    def __init__(self, message: str = "GitHub integration error", status_code: int = 502):
        super().__init__(message=message, status_code=status_code)


class GitHubAuthenticationException(GitHubIntegrationException):
    """Raised when GitHub App authentication or JWT creation fails."""

    def __init__(self, message: str = "GitHub authentication failed"):
        super().__init__(message=message, status_code=401)


class GitHubInvalidSignatureException(GitHubAuthenticationException):
    """Raised when a GitHub webhook signature is missing, malformed, or invalid."""

    def __init__(self, message: str = "Invalid GitHub webhook signature"):
        super().__init__(message=message)


class GitHubDuplicateDeliveryException(GitHubIntegrationException):
    """Raised when a duplicate webhook delivery ID is detected."""

    def __init__(self, message: str = "Duplicate GitHub webhook delivery ID"):
        super().__init__(message=message, status_code=200)


class GitHubInstallationNotFoundException(GitHubIntegrationException):
    """Raised when a specified GitHub installation ID is invalid or not found."""

    def __init__(self, message: str = "GitHub installation not found"):
        super().__init__(message=message, status_code=404)


class GitHubPermissionDeniedException(GitHubIntegrationException):
    """Raised when GitHub returns forbidden or insufficient scope/permission errors."""

    def __init__(self, message: str = "GitHub permission denied"):
        super().__init__(message=message, status_code=403)


class GitHubResourceNotFoundException(GitHubIntegrationException):
    """Raised when a requested GitHub API resource is not found."""

    def __init__(self, message: str = "GitHub resource not found"):
        super().__init__(message=message, status_code=404)


class GitHubRateLimitException(GitHubIntegrationException):
    """Raised when GitHub API rate limits are hit."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message=message, status_code=429)
        self.retry_after = retry_after


class GitHubValidationErrorException(GitHubIntegrationException):
    """Raised when GitHub returns 422 Unprocessable Entity / validation errors."""

    def __init__(self, message: str = "GitHub API validation error"):
        super().__init__(message=message, status_code=422)


class GitHubAPIException(GitHubIntegrationException):
    """Generic fallback for unhandled or unexpected GitHub API response errors."""

    def __init__(self, message: str = "GitHub API request failed", status_code: int = 502):
        super().__init__(message=message, status_code=status_code)
