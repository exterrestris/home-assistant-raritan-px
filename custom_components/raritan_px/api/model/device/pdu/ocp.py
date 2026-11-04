"""Raritan PDU API PDU OCP models."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from custom_components.raritan_px.api.model.device import RaritanDeviceSensors, RaritanEnergyDevice
from custom_components.raritan_px.api.model.sensor import (
    RaritanAccumulatingSensor,
    RaritanNumericSensor,
    RaritanStateSensor,
)

if TYPE_CHECKING:
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet


@dataclass(kw_only=True)
class RaritanPduOverCurrentProtector(RaritanEnergyDevice):
    """Representation of a Raritan PDU OCP."""

    sensors: RaritanPduOverCurrentProtectorSensors
    inlet_rid: str

    @property
    def device_type(self) -> str:
        """Return the type of this device."""
        return "Overcurrent Protector"

    @property
    def inlet(self) -> RaritanPduInlet | None:
        """Return the inlet supplying power to this device."""
        return self.pdu.inlets[self.inlet_rid] if self.pdu else None


@dataclass(kw_only=True)
class RaritanPduOverCurrentProtectorSensors(RaritanDeviceSensors):
    """Representation of the set of PDU OCP sensors."""

    trip: RaritanStateSensor | None = None
    voltage: RaritanNumericSensor | None = None
    current: RaritanNumericSensor | None = None
    peak_current: RaritanNumericSensor | None = None
    maximum_current: RaritanNumericSensor | None = None
    active_power: RaritanNumericSensor | None = None
    reactive_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    power_factor: RaritanNumericSensor | None = None
    displacement_power_factor: RaritanNumericSensor | None = None
    crest_factor: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None
    phase_angle: RaritanNumericSensor | None = None
    line_frequency: RaritanNumericSensor | None = None
    residual_current: RaritanNumericSensor | None = None
    residual_ac_current: RaritanNumericSensor | None = None
    residual_dc_current: RaritanNumericSensor | None = None
    residual_current_status: RaritanStateSensor | None = None
