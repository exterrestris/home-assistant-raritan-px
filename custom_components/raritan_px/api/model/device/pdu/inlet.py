"""Raritan PDU API PDU inlet models."""

from dataclasses import dataclass

from custom_components.raritan_px.api.model.device import RaritanDeviceSensors, RaritanEnergyDevice
from custom_components.raritan_px.api.model.sensor import (
    RaritanAccumulatingSensor,
    RaritanNumericSensor,
    RaritanStateSensor,
)


@dataclass(kw_only=True)
class RaritanPduInlet(RaritanEnergyDevice):
    """Representation of a Raritan PDU inlet."""

    inlet_id: int
    sensors: RaritanPduInletSensors


@dataclass(kw_only=True)
class RaritanPduInletSensors(RaritanDeviceSensors):
    """Representation of the set of PDU inlet sensors."""

    voltage: RaritanNumericSensor | None = None
    current: RaritanNumericSensor | None = None
    peak_current: RaritanNumericSensor | None = None
    residual_current: RaritanNumericSensor | None = None
    residual_ac_current: RaritanNumericSensor | None = None
    residual_dc_current: RaritanNumericSensor | None = None
    active_power: RaritanNumericSensor | None = None
    reactive_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    power_factor: RaritanNumericSensor | None = None
    displacement_power_factor: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None
    unbalanced_current: RaritanNumericSensor | None = None
    unbalanced_line_line_current: RaritanNumericSensor | None = None
    unbalanced_voltage: RaritanNumericSensor | None = None
    unbalanced_line_line_voltage: RaritanNumericSensor | None = None
    line_frequency: RaritanNumericSensor | None = None
    phase_angle: RaritanNumericSensor | None = None
    crest_factor: RaritanNumericSensor | None = None
    voltage_total_harmonic_distortion: RaritanNumericSensor | None = None
    current_total_harmonic_distortion: RaritanNumericSensor | None = None
    power_quality: RaritanStateSensor | None = None
    surge_protector_status: RaritanStateSensor | None = None
    residual_current_status: RaritanStateSensor | None = None
