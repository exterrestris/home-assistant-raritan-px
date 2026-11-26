"""Raritan PDU API PDU outlet sensor state enums."""

from enum import Enum, auto
from typing import TYPE_CHECKING, Self

from raritan.rpc.pdumodel import Outlet

from custom_components.raritan_px.api.model.sensor.state import OnOff
from custom_components.raritan_px.api.model.state import RaritanFlagState, RaritanState

if TYPE_CHECKING:
    from raritan.rpc import Enumeration


class OutletLedState(RaritanFlagState):
    """Outlet LED states."""

    OFF = 0
    RED = auto()
    GREEN = auto()
    BLINKING = auto()

    @classmethod
    def from_api(cls, value: Outlet.LedState) -> Self:
        """Convert from API 'enum'."""
        combined = cls(OutletLedState.OFF)

        if value.red:
            combined |= cls(OutletLedState.RED)

        if value.green:
            combined |= cls(OutletLedState.GREEN)

        if value.blinking:
            combined |= cls(OutletLedState.BLINKING)

        return combined


class OutletPowerState(RaritanState, Enum):
    """Outlet power states."""

    OFF = OnOff.OFF
    ON = OnOff.ON

    @classmethod
    def from_api(cls, value: Enumeration) -> Self:
        """Convert from API 'enum'."""
        match value:
            case Outlet.PowerState.PS_ON:  # pyright: ignore[reportAttributeAccessIssue]
                return cls(OutletPowerState.ON)
            case Outlet.PowerState.PS_OFF:  # pyright: ignore[reportAttributeAccessIssue]
                return cls(OutletPowerState.OFF)

        raise KeyError

    def to_api(self) -> Outlet.PowerState:
        """Convert to API 'enum'."""
        match self:
            case self.ON:
                return Outlet.PowerState.PS_ON  # pyright: ignore[reportAttributeAccessIssue]
            case self.OFF:
                return Outlet.PowerState.PS_OFF  # pyright: ignore[reportAttributeAccessIssue]
