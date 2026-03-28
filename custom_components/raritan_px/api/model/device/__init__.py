from dataclasses import dataclass, field, fields
from more_itertools import flatten

from .sensors import (
    RaritanDeviceSensors,
    RaritanPduInletSensors,
    RaritanPduSensors,
    RaritanPduOutletSensors
)
from ..sensor import RaritanSensor


@dataclass
class RaritanPduDevice:
    """Representation of a generic Raritan device."""

    device_id: str
    pdu_id: int
    name: str
    sensors: RaritanDeviceSensors

    @property
    def available_sensors(self) -> list[tuple[str, RaritanSensor]]:
        return [(sensor.name, getattr(self.sensors, sensor.name)) for sensor in fields(self.sensors) if getattr(self.sensors, sensor.name) is not None]


@dataclass
class RaritanPduEnergyDevice(RaritanPduDevice):
    """Representation of a generic Raritan energy device."""

    label: str


@dataclass
class RaritanPduOutlet(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU outlet."""

    outlet_id: int
    is_switchable: bool
    sensors: RaritanPduOutletSensors


@dataclass
class RaritanPduInlet(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU inlet."""

    inlet_id: int
    sensors: RaritanPduInletSensors


@dataclass
class RaritanPduOverCurrentProtector(RaritanPduEnergyDevice):
    """Representation of a Raritan PDU OCP."""

    ocp_id: int


@dataclass
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
    def available_sensors(self) -> list[tuple[str, RaritanSensor]]:
        return list(flatten([super().available_sensors] + [outlet.available_sensors for outlet in self.outlets] + [inlet.available_sensors for inlet in self.inlets]))
