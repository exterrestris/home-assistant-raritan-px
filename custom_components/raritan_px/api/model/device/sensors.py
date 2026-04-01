from dataclasses import dataclass
from typing import Self, get_type_hints, get_args

from raritan.rpc.sensors import Sensor

from ..sensor import (
    RaritanAccumulatingSensor,
    RaritanNumericSensor,
    RaritanSensor,
    RaritanStateSensor,
    RaritanMultiStateSensor,
    RaritanSwitch
)

@dataclass(kw_only=True)
class RaritanDeviceSensors:
    """Representation of a set of device sensors."""

    def __getitem__(self, key) -> RaritanSensor:
        return getattr(self, key)

    @classmethod
    def from_sensor_sources(cls, sources: dict[str, Sensor | None]) -> Self:
        types = get_type_hints(cls)

        return cls(
            **{
                name: sensor_type(source=src)
                for (name, (sensor_type, _), src) in [
                    (name, get_args(types[name]), src)
                    for name, src in sources.items()
                    if name in types and isinstance(src, Sensor)
                ]
            }, **{
                name: sensor_type.from_sensor_sources(src)
                for (name, (sensor_type, _), src) in [
                    (name, get_args(types[name]), src)
                    for name, src in sources.items()
                    if name in types and type(src) is list
                ]
            },
        )


@dataclass(kw_only=True)
class RaritanPduSensors(RaritanDeviceSensors):
    """Representation of the set of PDU device sensors."""

    power_supply_status: RaritanMultiStateSensor | None = None
    active_power: RaritanNumericSensor | None = None
    apparent_power: RaritanNumericSensor | None = None
    active_energy: RaritanAccumulatingSensor | None = None
    apparent_energy: RaritanAccumulatingSensor | None = None


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
