"""Constants/enums for API client."""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, Flag, auto
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

    from custom_components.raritan_px.api.model import RaritanUpdatable, RaritanUpdatableRpcMethodsList
    from custom_components.raritan_px.api.model.device import RaritanDevice

FIRMWARE_UPGRADE_WAIT_INTERVAL: Final[float] = 10
FIRMWARE_UPGRAGE_WAIT_MAX_ERRORS: Final[int] = 6

FIRMWARE_UPDATE_CHECK_CACHE_RESULT_FOR: Final[timedelta] = timedelta(seconds=2)
FIRMWARE_UPDATE_PREVENT_CHECKS_AFTER_START_FOR: Final[timedelta] = timedelta(seconds=20)


class PduDevices(Flag):
    """Flag to specify what sensor information to update."""

    NONE = 0
    INLETS = auto()
    OUTLETS = auto()
    OCPS = auto()
    ALL = INLETS | OUTLETS | OCPS


class UpdateSensors(Flag):
    """Flag to specify what sensor information to update."""

    NONE = 0
    INFO = auto()
    READINGS = auto()
    ALL = INFO | READINGS


class SensorUpdate(Enum):
    """Enum to determine what sensor data to update."""

    @dataclass(frozen=True)
    class _SensorUpdateMethod:
        method: Callable[[RaritanUpdatable], RaritanUpdatableRpcMethodsList]

    INFO = _SensorUpdateMethod(lambda sensor: sensor.update_info())
    READINGS = _SensorUpdateMethod(lambda sensor: sensor.update_readings())

    def get_update_methods(self, sensor: RaritanUpdatable) -> RaritanUpdatableRpcMethodsList:
        """Get the update methods for this sensor data update type."""
        return self.value.method(sensor)

    def fetch_msg(self, device: RaritanDevice, device_count: int, sensor_count: int) -> Callable[[], str]:
        """Get the message for this sensor data update type."""
        return lambda: (
            f"sensor {self.name.lower()} from {device.device_id} for {sensor_count} sensors across {device_count} devices"  # noqa: E501
        )
