"""API client errors."""


class RaritanClientError(Exception):
    """Base exception for all client exceptions."""


class ConfigError(RaritanClientError):
    """Raised when configuration is invalid."""


class CommunicationError(RaritanClientError):
    """Raised when a generic error occurs while communicating with the Raritan API."""


class RequestRefusedError(CommunicationError):
    """Raised when connection is refused."""


class RequestError(CommunicationError):
    """Raised when a generic error occurs for a request."""


class HttpError(RequestError):
    """Raised when a generic HTTP error occurs while communicating with the Raritan API."""

    code: int | None

    def __init__(self, *args: object, code: int | None) -> None:
        """Initialise the exception."""
        super().__init__(*args)
        self.code = code


class RequestTimeoutError(RequestError):
    """Raised when HTTP request times out."""


class CertificateVerificationError(RequestError):
    """Raised when SSL certificate verification fails."""


class AuthenticationError(CommunicationError):
    """Raised for authentication errors."""


class UnauthorizedError(AuthenticationError, HttpError):
    """Raised when the request is unauthorised."""

    def __init__(self, *args: object) -> None:
        """Initialise the exception."""
        super().__init__(*args, code=401)


class ForbiddenError(AuthenticationError, HttpError):
    """Raised when the authenticated user doesn't have permission to make the request."""

    def __init__(self, *args: object) -> None:
        """Initialise the exception."""
        super().__init__(*args, code=403)


class JsonRpcError(CommunicationError):
    """Raised when a generic JSON-RPC error occurs communicating with the Raritan API."""


class JsonRpcSyntaxError(JsonRpcError):
    """Raised when a JSON-RPC repsonse from the Raritan API has syntax errors."""


class JsonRpcDecodeError(JsonRpcError):
    """Raised when a JSON-RPC from the Raritan API cannot be decoded."""


class InsufficientPrivilegesError(JsonRpcError):
    """Raised when a request fails due to insufficient user privileges."""


class SessionError(CommunicationError):
    """Raised when session operations fail."""


class ConcurrentLoginError(AuthenticationError, SessionError):
    """Raised when creation of a new session fails due single login limitation."""


class SessionCloseError(SessionError):
    """Raised when closing the current session."""
