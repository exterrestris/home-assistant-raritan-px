"""Raritan PDU API base device models."""

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Self, get_args, get_type_hints

from raritan.rpc.sensors import Sensor

from custom_components.raritan_px.api.model import RaritanModel
from custom_components.raritan_px.api.model.sensor import RaritanSensor, RaritanSwitch

if TYPE_CHECKING:
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu


@dataclass(kw_only=True)
class RaritanDevice(RaritanModel):
    """Representation of a generic Raritan device."""

    id: int
    rid: str
    device_id: str
    name: str
    url: str | None = None
    sensors: RaritanDeviceSensors

    @property
    def defined_sensors(self) -> list[tuple[str, str, RaritanSensor | None]]:
        """Return a list of sensors defined on this device by sensor name."""
        return [(self.device_id, sensor.name, getattr(self.sensors, sensor.name)) for sensor in fields(self.sensors)]

    @property
    def all_defined_sensors(self) -> list[tuple[str, str, RaritanSensor | None]]:
        """Return a list of sensors defined on this device by device ID and sensor name."""
        return [(name, sensor_name, sensor) for (name, sensor_name, sensor) in self.defined_sensors]

    @property
    def updatable_sensors(self) -> list[tuple[str, str, RaritanSensor]]:
        """Return a list of updatable sensors defined on this device by sensor name."""
        return [
            (name, sensor_name, sensor) for (name, sensor_name, sensor) in self.defined_sensors if sensor is not None
        ]

    @property
    def all_updatable_sensors(self) -> list[tuple[str, str, RaritanSensor]]:
        """Return a list of updatable sensors defined on this device by device ID and sensor name."""
        return [
            (name, sensor_name, sensor)
            for (name, sensor_name, sensor) in self.all_defined_sensors
            if sensor is not None
        ]

    @property
    def available_sensors(self) -> list[tuple[str, RaritanSensor]]:
        """Return a list of available sensors defined on this device by sensor name."""
        return [
            (f"{sensor_name}:{idx}" if idx is not None else sensor_name, sensor)
            for (_, sensor_name, _sensor) in self.updatable_sensors
            for (idx, sensor) in _sensor.sensors
        ]

    @property
    def available_switches(self) -> list[tuple[str, RaritanSwitch]]:
        """Return a list of available switches defined on this device by switch name."""
        return [
            (sensor_name, sensor)
            for (_, sensor_name, sensor) in self.defined_sensors
            if isinstance(sensor, RaritanSwitch)
        ]

    @property
    def device_name(self) -> str:
        """Return the name for this device if defined, or a default name."""
        return self.name

    @property
    def device_type(self) -> str:
        """Return the type of this device."""
        raise NotImplementedError

    @property
    def device_model(self) -> str:
        """Return the model of this device."""
        raise NotImplementedError

    @property
    def pdu(self) -> RaritanPdu:
        """Return the pdu for this device."""
        raise NotImplementedError


@dataclass(kw_only=True)
class RaritanEnergyDevice(RaritanDevice):
    """Representation of a generic Raritan energy device."""

    label: str
    _pdu: RaritanPdu = field(init=False, repr=False)

    @property
    def pdu(self) -> RaritanPdu:
        """Get the pdu for this entity."""
        return self._pdu

    @pdu.setter
    def pdu(self, pdu: RaritanPdu) -> None:
        self._pdu = pdu

    @property
    def device_name(self) -> str:
        """Get the device name to use for this entity."""
        if self.name:
            return self.name

        return f"{self.device_type} {self.label}"

    @property
    def device_model(self) -> str:
        """Get the model to use for this entity."""
        return f"{self.pdu.model} {self.device_type}"


@dataclass(kw_only=True)
class RaritanDeviceSensors:
    """Representation of a set of device sensors."""

    def __getitem__(self, key: str) -> RaritanSensor:
        """Return a specific sensor by its name."""
        return getattr(self, key)

    @classmethod
    def from_sensor_sources(cls, sources: dict[str, Sensor | None]) -> Self:
        """Build a class instance from a list of sensor sources."""
        types = get_type_hints(cls)

        return cls(
            **{
                name: sensor_type(source=src)
                for (name, (sensor_type, _), src) in [
                    (name, get_args(types[name]), src)
                    for name, src in sources.items()
                    if name in types and isinstance(src, Sensor)
                ]
            },
            **{
                name: sensor_type.from_sensor_sources(src)
                for (name, (sensor_type, _), src) in [
                    (name, get_args(types[name]), src)
                    for name, src in sources.items()
                    if name in types and type(src) is list
                ]
            },
        )
