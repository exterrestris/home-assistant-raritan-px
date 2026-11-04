"""Raritan PDU API PDU outlet models."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from custom_components.raritan_px.api.model.device import RaritanDeviceSensors, RaritanEnergyDevice
from custom_components.raritan_px.api.model.sensor import RaritanAccumulatingSensor, RaritanNumericSensor, RaritanSwitch

if TYPE_CHECKING:
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector


@dataclass(kw_only=True)
class RaritanPduOutlet(RaritanEnergyDevice):
    """Representation of a Raritan PDU outlet."""

    is_switchable: bool
    receptacle_type: str
    inlet_rid: str
    ocp_rid: str
    sensors: RaritanPduOutletSensors

    @property
    def device_type(self) -> str:
        """Return the type of this device."""
        return "Outlet"

    @property
    def inlet(self) -> RaritanPduInlet | None:
        """Return the inlet supplying power to this device."""
        return self.pdu.inlets[self.inlet_rid] if self.pdu else None

    @property
    def ocp(self) -> RaritanPduOverCurrentProtector | None:
        """Return the overcurrent protector supplying power to this device."""
        return self.pdu.ocps[self.ocp_rid] if self.pdu else None


@dataclass(kw_only=True)
class RaritanPduOutletSensors(RaritanDeviceSensors):
    """Representation of the set of PDU outlet sensors."""

    voltage: RaritanNumericSensor | None = None
    current: RaritanNumericSensor | None = None
    peak_current: RaritanNumericSensor | None = None
    maximum_current: RaritanNumericSensor | None = None
    unbalanced_current: RaritanNumericSensor | None = None
    active_power: RaritanNumericSensor | None = None
    reactive_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    power_factor: RaritanNumericSensor | None = None
    displacement_power_factor: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None
    phase_angle: RaritanNumericSensor | None = None
    line_frequency: RaritanNumericSensor | None = None
    crest_factor: RaritanNumericSensor | None = None
    voltage_total_harmonic_distortion: RaritanNumericSensor | None = None
    current_total_harmonic_distortion: RaritanNumericSensor | None = None
    inrush_current: RaritanNumericSensor | None = None
    outlet_state: RaritanSwitch | None = None
