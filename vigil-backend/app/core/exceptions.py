class VigilException(Exception):
    """Base exception for all custom VIGIL application exceptions."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundException(VigilException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class ServiceUnavailableException(VigilException):
    """Exception raised when an upstream service or dependency is unavailable."""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message=message, status_code=503)


class UnauthorizedException(VigilException):
    """Exception raised when the request is not authenticated (HTTP 401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(VigilException):
    """Exception raised when an authenticated user lacks permission (HTTP 403)."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message=message, status_code=403)


class ConflictException(VigilException):
    """Exception raised on concurrent modification or duplicate-state conflict (HTTP 409)."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(message=message, status_code=409)


class InvalidStateTransitionException(VigilException):
    """Exception raised when a requested state transition is not valid (HTTP 422)."""

    def __init__(self, message: str = "Invalid state transition"):
        super().__init__(message=message, status_code=422)

