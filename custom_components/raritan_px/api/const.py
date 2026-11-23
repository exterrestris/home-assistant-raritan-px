"""Raritan API client constants."""

from typing import Final

PING_TIMEOUT: Final[int] = 5
API_TIMEOUT: Final[int] = 10
FIRMWARE_UPLOAD_TIMEOUT: Final[int] = 60

DEFAULT_PORT: Final[int] = 443
DEFAULT_USERNAME: Final[str] = "admin"
DEFAULT_PASSWORD: Final[str] = "raritan"  # noqa: S105  # This is the default factory password for Raritan PDUs
