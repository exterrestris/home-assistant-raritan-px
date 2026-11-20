"""Raritan PDU API PDU outlet sensor state enums."""

from enum import Enum, Flag, auto
from typing import TYPE_CHECKING

from raritan.rpc.pdumodel import Outlet

from custom_components.raritan_px.api.model.sensor.state import OnOff
from custom_components.raritan_px.api.model.state import RaritanState

if TYPE_CHECKING:
    from raritan.rpc import Enumeration


class RaritanOutletState(RaritanState):
    """Generic outlet state enum."""


class OutletLedState(RaritanOutletState, Flag):
    """Outlet LED states."""

    OFF = 0
    RED = auto()
    GREEN = auto()
    BLINKING = auto()

    @staticmethod
    def from_api(value: Outlet.LedState) -> OutletLedState:
        """Convert from API 'enum'."""
        combined = OutletLedState.OFF

        if value.red:
            combined |= OutletLedState.RED

        if value.green:
            combined |= OutletLedState.GREEN

        if value.blinking:
            combined |= OutletLedState.BLINKING

        return combined


class OutletPowerState(RaritanOutletState, Enum):
    """Outlet power states."""

    OFF = OnOff.OFF
    ON = OnOff.ON

    @staticmethod
    def from_api(value: Enumeration) -> OutletPowerState:
        """Convert from API 'enum'."""
        match value:
            case Outlet.PowerState.PS_ON:  # pyright: ignore[reportAttributeAccessIssue]
                return OutletPowerState.ON
            case Outlet.PowerState.PS_OFF:  # pyright: ignore[reportAttributeAccessIssue]
                return OutletPowerState.OFF

        raise KeyError

    def to_api(self) -> Outlet.PowerState:
        """Convert to API 'enum'."""
        match self:
            case OutletPowerState.ON:
                return Outlet.PowerState.PS_ON  # pyright: ignore[reportAttributeAccessIssue]
            case OutletPowerState.OFF:
                return Outlet.PowerState.PS_OFF  # pyright: ignore[reportAttributeAccessIssue]
