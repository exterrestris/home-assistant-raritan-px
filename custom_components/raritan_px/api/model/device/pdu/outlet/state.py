"""Raritan PDU API PDU outlet sensor state enums."""

from enum import Enum, StrEnum

from custom_components.raritan_px.api.model.sensor.state import OnOff
from custom_components.raritan_px.api.model.state import RaritanState


class RaritanOutletState(RaritanState):
    """Generic outlet state enum."""


class OutletLedState(RaritanOutletState, StrEnum):
    """Outlet LED states."""

    RED = "red"
    GREEN = "green"
    BLINKING = "blinking"


class OutletPowerState(RaritanOutletState, Enum):
    """Outlet power states."""

    OFF = OnOff.OFF
    ON = OnOff.ON
