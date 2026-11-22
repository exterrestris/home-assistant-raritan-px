"""Raritan PDU API generic state enums."""

from abc import abstractmethod
from enum import Flag, IntEnum
from typing import TYPE_CHECKING, Any, Self

from custom_components.raritan_px.api import RaritanEnum

if TYPE_CHECKING:
    from raritan.rpc.pdumodel import Enumeration


class RaritanState:
    """Generic state enum."""

    @classmethod
    @abstractmethod
    def from_api(cls, value: Any) -> Self:
        """Convert from API value."""
        raise NotImplementedError


class RaritanEnumState(RaritanState, RaritanEnum, IntEnum):
    """Generic state enum."""

    @classmethod
    def from_api(cls, value: Enumeration) -> Self:
        """Convert from API value."""
        return cls(value.val)


class RaritanFlagState(RaritanState, Flag):
    """Generic state enum."""
