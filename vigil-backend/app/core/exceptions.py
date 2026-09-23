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
