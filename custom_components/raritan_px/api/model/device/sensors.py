from dataclasses import dataclass
from typing import Self, get_type_hints, get_args

from raritan.rpc.sensors import Sensor

from ..sensor import (
    RaritanNumericSensor,
    RaritanSensor,
    RaritanSwitch
)

@dataclass
class RaritanDeviceSensors:
    """Representation of a set of device sensors."""

    def __getitem__(self, key) -> RaritanSensor:
        return getattr(self, key)

    @classmethod
    def from_sensor_sources(cls, sources: dict[str, Sensor | None]) -> Self:
        types = get_type_hints(cls)

        return cls(**{
            name: sensor_type(source)
            for (name, (sensor_type, _), source) in [(name, get_args(types[name]), source) for
                name, source in sources.items()
                if name in types and source is not None
            ]
        })


@dataclass
class RaritanPduSensors(RaritanDeviceSensors):
    """Representation of the set of PDU device sensors."""

    power_supply_status: RaritanStateSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanNumericSensor | None = None
    apparent_energy: RaritanNumericSensor | None = None


@dataclass
class RaritanPduInletSensors(RaritanDeviceSensors):
    """Representation of the set of PDU inlet sensors."""

    voltage: RaritanNumericSensor | None = None
    current: RaritanNumericSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanNumericSensor | None = None
    apparent_energy: RaritanNumericSensor | None = None


@dataclass
class RaritanPduOutletSensors(RaritanDeviceSensors):
    """Representation of the set of PDU outlet sensors."""

    voltage: RaritanNumericSensor | None = None
    current: RaritanNumericSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanNumericSensor | None = None
    apparent_energy: RaritanNumericSensor | None = None
    outlet_state: RaritanSwitch | None = None
