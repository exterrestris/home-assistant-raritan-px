"""API client errors."""

from typing import Any


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


class FirmwareVerificationError(RaritanClientError):
    """Base class for firmware verification exceptions."""


class NoUploadedFirmwareError(FirmwareVerificationError):
    """Base class for firmware upgrade exceptions."""


class InvalidFirmwareError(FirmwareVerificationError):
    """Base class for firmware upgrade exceptions."""


class UnsupportedModelFirmwareError(FirmwareVerificationError):
    """Base class for firmware upgrade exceptions."""


class IncompatibleFirmwareError(FirmwareVerificationError):
    """Base class for firmware upgrade exceptions."""


class FirmwareUpgradeError(RaritanClientError):
    """Base class for firmware upgrade exceptions."""


class NoFirmwareUpgradeInProgressError(FirmwareUpgradeError):
    """Raised when a firmware upgrade fails."""


class FirmwareUpgradeFailedError(FirmwareUpgradeError):
    """Raised when a firmware upgrade fails."""


class FirmwareUpgradeInProgressError(FirmwareUpgradeError):
    """Raised when JSON-RPC API is unavailable due to firmware upgrade."""

    elapsed: int
    estimated: int
    state: str

    def __init__(self, state: str, elapsed: int, estimated: int) -> None:
        """Init the exception."""
        super().__init__()
        self.elapsed = elapsed
        self.estimated = estimated
        self.state = state

    def __reduce__(self) -> str | tuple[Any, ...]:
        """Allow pickling the exception."""
        return (FirmwareUpgradeInProgressError, (self.state, self.elapsed, self.estimated))
