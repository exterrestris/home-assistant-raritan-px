from dataclasses import dataclass
from typing import Self

from raritan.rpc.sensors import AccumulatingNumericSensor, NumericSensor, Sensor, StateSensor

from ..sensor import RaritanAccumulatingSensor, RaritanNumericSensor, RaritanSensor, RaritanStateSensor

@dataclass
class RaritanDeviceSensors:
    """Representation of a set of device sensors."""

    def __getitem__(self, key) -> RaritanSensor:
        return getattr(self, key)

    @classmethod
    def from_sensor_sources(cls, sources: dict[str, Sensor | None]) -> Self:
        state_sensors = {
            name: RaritanStateSensor(source)
            for name, source in sources.items()
            if isinstance(source, StateSensor)
        }
        numeric_sensors = {
            name: RaritanNumericSensor(source)
            for name, source in sources.items()
            if isinstance(source, NumericSensor) and not isinstance(source, AccumulatingNumericSensor)
        }
        accumulating_sensors = {
            name: RaritanAccumulatingSensor(source)
            for name, source in sources.items()
            if isinstance(source, AccumulatingNumericSensor)
        }

        return cls(**state_sensors, **numeric_sensors, **accumulating_sensors)


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
