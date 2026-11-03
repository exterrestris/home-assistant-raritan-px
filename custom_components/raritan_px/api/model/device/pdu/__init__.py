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
    voltage_rating: str
    current_rating: str
    frequency_rating: str
    power_rating: str
    sensors: RaritanPduSensors
    outlets: list[RaritanPduOutlet] = field(default_factory=list[RaritanPduOutlet])
    inlets: list[RaritanPduInlet] = field(default_factory=list[RaritanPduInlet])
    ocps: list[RaritanPduOverCurrentProtector] = field(default_factory=list[RaritanPduOverCurrentProtector])

    def add_outlet(self, outlet: RaritanPduOutlet) -> RaritanPduOutlet:
        """Add an outlet to the PDU."""
        outlet.pdu = self
        self.outlets.append(outlet)

        return outlet

    def add_inlet(self, inlet: RaritanPduInlet) -> RaritanPduInlet:
        """Add an inlet to the PDU."""
        inlet.pdu = self
        self.inlets.append(inlet)

        return inlet

    def add_ocp(self, ocp: RaritanPduOverCurrentProtector) -> RaritanPduOverCurrentProtector:
        """Add an overcurrent protector to the PDU."""
        ocp.pdu = self
        self.ocps.append(ocp)

        return ocp

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

    @property
    def pdu(self) -> RaritanPdu:
        """Return this pdu."""
        return self

    @property
    def device_name(self) -> str:
        """Get the device name to use for this entity."""
        if self.name:
            return self.name

        return f"{self.model} {self.serial_number}"

    @property
    def device_model(self) -> str:
        """Get the device model to use for this entity."""
        return self.model

    @property
    def device_type(self) -> str:
        """Get the device type to use for this entity."""
        return "PDU"


@dataclass(kw_only=True)
class RaritanPduSensors(RaritanDeviceSensors):
    """Representation of the set of PDU device sensors."""

    power_supply_status: RaritanMultiStateSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None
