"""Raritan PDU API generic state enums."""

from abc import abstractmethod
from typing import Any


class RaritanState:
    """Generic state enum."""

    @staticmethod
    @abstractmethod
    def from_api(value: Any) -> RaritanState:
        """Convert from API value."""
        raise NotImplementedError
