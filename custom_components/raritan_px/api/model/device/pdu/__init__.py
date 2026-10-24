"""Raritan PDU API PDU models."""

from dataclasses import dataclass, field

from more_itertools import flatten

from custom_components.raritan_px.api.model.device import (
    RaritanDevice,
    RaritanDeviceSensors,
)
from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector
from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
from custom_components.raritan_px.api.model.sensor import (
    RaritanAccumulatingSensor,
    RaritanMultiStateSensor,
    RaritanNumericSensor,
    RaritanSensor,
)


@dataclass(kw_only=True)
class RaritanPdu(RaritanDevice):
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

    def add_outlet(self, outlet: RaritanPduOutlet) -> None:
        """Add an outlet to the PDU."""
        self.outlets.append(outlet)

    def add_inlet(self, inlet: RaritanPduInlet) -> None:
        """Add an inlet to the PDU."""
        self.inlets.append(inlet)

    def add_ocp(self, ocp: RaritanPduOverCurrentProtector) -> None:
        """Add an overcurrent protector to the PDU."""
        self.ocps.append(ocp)

    @property
    def all_defined_sensors(self) -> list[tuple[str, str, RaritanSensor | None]]:
        """Return a list of sensors defined on this device and child devices by device ID and sensor name."""
        return list(
            flatten(
                [super().all_defined_sensors]
                + [outlet.all_defined_sensors for outlet in self.outlets]
                + [inlet.all_defined_sensors for inlet in self.inlets]
            )
        )


@dataclass(kw_only=True)
class RaritanPduSensors(RaritanDeviceSensors):
    """Representation of the set of PDU device sensors."""

    power_supply_status: RaritanMultiStateSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None
