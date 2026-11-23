"""API client errors."""


class RaritanClientError(Exception):
    """Base exception for all client exceptions."""


class ConfigError(RaritanClientError):
    """Raised when configuration is invalid."""


class CommunicationError(RaritanClientError):
    """Raised when a generic error occurs while communicating with the Raritan API."""


class RequestRefusedError(CommunicationError):
    """Raised when connection is refused."""


class HttpError(CommunicationError):
    """Raised when a generic HTTP error occurs while communicating with the Raritan API."""


class RequestTimeoutError(HttpError):
    """Raised when HTTP request times out."""


class CertificateVerificationError(HttpError):
    """Raised when SSL certificate verification fails."""


class AuthenticationError(CommunicationError):
    """Raised when authentication fails."""


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
