"""Raritan PDU API device sensor state enums."""

from enum import Enum, IntEnum


class RaritanSensorState(Enum):
    """Generic sensor state enum."""

    def friendly_name(self) -> str:
        """Return a formatted 'friendly' name for the sensor state."""
        return self.name.title()

    @classmethod
    def options(cls) -> list[str]:
        """Return a list of the 'friendly' names for all the possible sensor states."""
        return [opt.friendly_name() for opt in list(cls)]


class OnOff(RaritanSensorState, IntEnum):
    """On/Off sensor state enum."""

    OFF = 0
    ON = 1


class OpenClosed(RaritanSensorState, IntEnum):
    """Open/Closed sensor state enum."""

    OPEN = 0
    CLOSED = 1


class NormalAlarmed(RaritanSensorState, IntEnum):
    """Normal/Alarmed sensor state enum."""

    NORMAL = 0
    ALARMED = 1


class OkFaulted(RaritanSensorState, IntEnum):
    """OK/Faulted sensor state enum."""

    OK = 0
    FAULT = 1


class ResidualCurrentStatus(RaritanSensorState, IntEnum):
    """RCD sensor state enum."""

    NORMAL = 0
    WARNING = 1
    CRITICAL = 2
    SELF_TEST = 3
    FAILURE = 4
