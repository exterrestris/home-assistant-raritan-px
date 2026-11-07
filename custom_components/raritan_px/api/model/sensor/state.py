"""Raritan PDU API device sensor state enums."""

from enum import IntEnum

from custom_components.raritan_px.api import RaritanEnum


class RaritanSensorState(RaritanEnum):
    """Generic sensor state enum."""


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
