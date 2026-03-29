from dataclasses import dataclass, field, fields
from itertools import product
from more_itertools import flatten

from .. import RaritanUpdatable
from ..sensor import RaritanSensor, RaritanMultiSensor, RaritanSwitch
from .sensors import (
    RaritanDeviceSensors,
    RaritanPduInletSensors,
    RaritanPduSensors,
    RaritanPduOutletSensors
)

@dataclass(kw_only=True)
class RaritanPduDevice:
    """Representation of a generic Raritan device."""

    device_id: str
    pdu_id: int
    name: str
    sensors: RaritanDeviceSensors

    @property
    def defined_sensors(self) -> list[tuple[str, RaritanSensor | None]]:
        return [
            (sensor.name, getattr(self.sensors, sensor.name)) for sensor in fields(self.sensors)
        ]

    @property
    def all_defined_sensors(self) -> list[tuple[str, str, RaritanSensor | None]]:
        return [
            (self.device_id, sensor_name, sensor) for (sensor_name, sensor) in self.defined_sensors
        ]

    @property
    def updatable_sensors(self) -> list[tuple[str, RaritanSensor]]:
        return [
            (name, sensor) for (name, sensor) in self.defined_sensors if sensor is not None
        ]

    @property
    def all_updatable_sensors(self) -> list[tuple[str, str, RaritanSensor]]:
        return [
            (name, sensor_name, sensor) for (name, sensor_name, sensor) in self.all_defined_sensors if sensor is not None
        ]

    @property
    def available_sensors(self) -> list[tuple[str, RaritanSensor]]:
        return [
            (name, sensor) for (name, sensor) in self.updatable_sensors if not isinstance(sensor, RaritanMultiSensor)
        ] + [
            (f"{name}:{idx}", sensor)
            for (name, (idx, sensor)) in list(flatten([
                list(product([name], enumerate(sensorlist.sensors)))
                for (name, sensorlist) in self.updatable_sensors
                if isinstance(sensorlist, RaritanMultiSensor)
            ]))
        ]

    @property
    def available_switches(self) -> list[tuple[str, RaritanSwitch]]:
        return [
            (name, sensor) for (name, sensor) in self.defined_sensors if isinstance(sensor, RaritanSwitch)
        ]


@dataclass(kw_only=True)
class RaritanPduEnergyDevice(RaritanPduDevice):
    """Representation of a generic Raritan energy device."""

    label: str


@dataclass(kw_only=True)
class RaritanPduOutlet(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU outlet."""

    outlet_id: int
    is_switchable: bool
    sensors: RaritanPduOutletSensors


@dataclass(kw_only=True)
class RaritanPduInlet(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU inlet."""

    inlet_id: int
    sensors: RaritanPduInletSensors


@dataclass(kw_only=True)
class RaritanPduOverCurrentProtector(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU OCP."""

    ocp_id: int


@dataclass(kw_only=True)
class RaritanPdu(RaritanPduDevice):
    """Representation of a Raritan PDU."""

    host: str
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    hardware_version: str
    mac_address: str
    has_switchable_outlets: bool
    has_metered_outlets: bool
    is_standalone: bool
    sensors: RaritanPduSensors
    outlets: list[RaritanPduOutlet] = field(default_factory=list[RaritanPduOutlet])
    inlets: list[RaritanPduInlet] = field(default_factory=list[RaritanPduInlet])
    ocps: list[RaritanPduOverCurrentProtector] = field(default_factory=list[RaritanPduOverCurrentProtector])

    def add_outlet(self, outlet: RaritanPduOutlet):
        self.outlets.append(outlet)

    def add_inlet(self, inlet: RaritanPduInlet):
        self.inlets.append(inlet)

    def add_ocp(self, ocp: RaritanPduOverCurrentProtector):
        self.ocps.append(ocp)

    @property
    def all_defined_sensors(self) -> list[tuple[str, str, RaritanSensor | None]]:
        return list(flatten([super().all_defined_sensors] + [outlet.all_defined_sensors for outlet in self.outlets] + [inlet.all_defined_sensors for inlet in self.inlets]))
