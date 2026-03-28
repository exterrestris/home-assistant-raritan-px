from enum import Enum, StrEnum

from ..sensor.states import OnOff

class RaritanState(Enum):
    """Generic state enum"""

class RaritanOutletState(RaritanState):
    """Generic outlet state enum"""


class OutletPowerState(RaritanOutletState, Enum):
    """Outlet power states"""

    OFF = OnOff.OFF
    ON = OnOff.ON


class OutletLedState(RaritanOutletState, StrEnum):
    """Outlet LED states"""

    RED = "red"
    GREEN = "green"
    BLINKING = "blinking"
