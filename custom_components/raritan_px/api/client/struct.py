"""Structures for API client."""

from dataclasses import dataclass
from typing import ClassVar, Final

from custom_components.raritan_px.api.const import API_TIMEOUT, DEFAULT_PORT


@dataclass(frozen=True)
class AuthenticationDetails:
    """Authentication information for Raritan API."""

    user: str
    passwd: str


@dataclass(frozen=True)
class ConnectionDetails:
    """Connection information for Raritan API."""

    _HTTPS: ClassVar[Final[str]] = "https"
    _HTTP: ClassVar[Final[str]] = "http"

    host: str
    auth: AuthenticationDetails | None = None
    port: int = DEFAULT_PORT
    use_ssl: bool = True
    verify_ssl: bool = True
    timeout: float = API_TIMEOUT

    @property
    def protocol(self) -> str:
        """Get the protocol for this config."""
        return self._HTTPS if self.use_ssl else self._HTTP
