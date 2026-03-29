
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Self, get_type_hints, get_args
from itertools import chain

from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfLength,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfReactiveEnergy,
    UnitOfReactivePower,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume
)

from raritan.rpc import Time
from raritan.rpc.sensors import AccumulatingNumericSensor, NumericSensor, Sensor, StateSensor

from .. import RaritanUpdatable, RaritanUpdatableRpcMethodsList
from .states import OnOff, OpenClosed, NormalAlarmed, OkFaulted, RaritanSensorState

SENSOR_UNITS_MAPPING: dict[int, str | None] = {
    Sensor.NONE: None,
    Sensor.VOLT: UnitOfElectricPotential.VOLT,
    Sensor.AMPERE: UnitOfElectricCurrent.AMPERE,
    Sensor.WATT: UnitOfPower.WATT,
    Sensor.VOLT_AMP: UnitOfApparentPower.VOLT_AMPERE,
    Sensor.WATT_HOUR: UnitOfEnergy.WATT_HOUR,
    # Sensor.VOLT_AMP_HOUR: ,
    Sensor.DEGREE_CELSIUS: UnitOfTemperature.CELSIUS,
    Sensor.HZ: UnitOfFrequency.HERTZ,
    Sensor.PERCENT: PERCENTAGE,
    Sensor.METER_PER_SEC: UnitOfSpeed.METERS_PER_SECOND,
    Sensor.PASCAL: UnitOfPressure.PA,
    # Sensor.G: ,
    Sensor.RPM: REVOLUTIONS_PER_MINUTE,
    Sensor.METER: UnitOfLength.METERS,
    Sensor.HOUR: UnitOfTime.HOURS,
    Sensor.MINUTE: UnitOfTime.MINUTES,
    Sensor.SECOND: UnitOfTime.SECONDS,
    Sensor.VOLT_AMP_REACTIVE: UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
    Sensor.VOLT_AMP_REACTIVE_HOUR: UnitOfReactiveEnergy.VOLT_AMPERE_REACTIVE_HOUR,
    Sensor.GRAM: UnitOfMass.GRAMS,
    # Sensor.OHM: ,
    # Sensor.LITERS_PER_HOUR: ,
    # Sensor.CANDELA: ,
    # Sensor.METER_PER_SQUARE_SEC: ,
    # Sensor.METER_PER_SQARE_SEC: ,
    # Sensor.TESLA: ,
    # Sensor.VOLT_PER_METER: ,
    # Sensor.VOLT_PER_AMPERE: ,
    Sensor.DEGREE: DEGREE,
    Sensor.DEGREE_FAHRENHEIT: UnitOfTemperature.CELSIUS,
    Sensor.KELVIN: UnitOfTemperature.KELVIN,
    Sensor.JOULE: UnitOfEnergy.JOULE,
    # Sensor.COULOMB: ,
    # Sensor.NIT: ,
    # Sensor.LUMEN: ,
    # Sensor.LUMEN_SECOND: ,
    # Sensor.LUX: ,
    Sensor.PSI: UnitOfPressure.PSI,
    # Sensor.NEWTON: ,
    Sensor.FOOT: UnitOfLength.FEET,
    Sensor.FOOT_PER_SEC: UnitOfSpeed.FEET_PER_SECOND,
    Sensor.CUBIC_METER: UnitOfVolume.CUBIC_METERS,
    # Sensor.RADIANT: ,
    # Sensor.STERADIANT: ,
    # Sensor.HENRY: ,
    # Sensor.FARAD: ,
    # Sensor.MOL: ,
    # Sensor.BECQUEREL: ,
    # Sensor.GRAY: ,
    # Sensor.SIEVERT: ,
    # Sensor.G_PER_CUBIC_METER: ,
    # Sensor.UG_PER_CUBIC_METER: ,
}

STATE_SENSOR_TYPE_VALUE_MAPPING: dict[type[RaritanSensorState], dict[int, RaritanSensorState]] = {
    OnOff: {
        Sensor.OnOffState.ON.val: OnOff.ON, # pyright: ignore[reportAttributeAccessIssue]
        Sensor.OnOffState.OFF.val: OnOff.OFF, # pyright: ignore[reportAttributeAccessIssue]
    },
    OpenClosed: {
        Sensor.OpenClosedState.OPEN.val: OpenClosed.OPEN, # pyright: ignore[reportAttributeAccessIssue]
        Sensor.OpenClosedState.CLOSED.val: OpenClosed.CLOSED, # pyright: ignore[reportAttributeAccessIssue]
    },
    NormalAlarmed: {
        Sensor.NormalAlarmedState.NORMAL.val: NormalAlarmed.NORMAL, # pyright: ignore[reportAttributeAccessIssue]
        Sensor.NormalAlarmedState.ALARMED.val: NormalAlarmed.ALARMED, # pyright: ignore[reportAttributeAccessIssue]
    },
    OkFaulted: {
        Sensor.OkFaultState.OK.val: OkFaulted.OK, # pyright: ignore[reportAttributeAccessIssue]
        Sensor.OkFaultState.FAULT.val: OkFaulted.FAULT, # pyright: ignore[reportAttributeAccessIssue]
    },
}

STATE_SENSOR_TYPE_MAPPING: dict[int, type[RaritanSensorState]] = {
    # On/Off State Sensors
    StateSensor.ON_OFF_SENSOR: OnOff,
    StateSensor.DRY_CONTACT: OnOff,
    StateSensor.POWERED_DRY_CONTACT: OnOff,

    # Open/Closed State Sensors
    StateSensor.TRIP_SENSOR: OpenClosed,
    StateSensor.DOOR_STATE: OpenClosed,
    StateSensor.DOOR_LOCK_STATE: OpenClosed,
    StateSensor.DOOR_HANDLE_LOCK: OpenClosed,

    # Normal/Alarmed State Sensors
    StateSensor.CONTACT_CLOSURE: NormalAlarmed,
    StateSensor.VIBRATION: NormalAlarmed,
    StateSensor.WATER_LEAK: NormalAlarmed,
    StateSensor.SMOKE_DETECTOR: NormalAlarmed,
    StateSensor.OCCUPANCY: NormalAlarmed,
    StateSensor.TAMPER: NormalAlarmed,
    StateSensor.CONTACT_CLOSURE: NormalAlarmed,
    StateSensor.CONTACT_CLOSURE: NormalAlarmed,
    StateSensor.CONTACT_CLOSURE: NormalAlarmed,

    # Normal/Alarmed State Sensors if Discrete
    StateSensor.MAGNETIC_FIELD_STRENGTH: NormalAlarmed,
    StateSensor.FAULT_STATE: NormalAlarmed,
}

STATE_SENSOR_READING_TYPE = {
    StateSensor.NUMERIC: 0,
    StateSensor.DISCRETE_ON_OFF: 1, #  Sensor has two discrete readings: 0 (off) and 1 (on), see OnOffState
    StateSensor.DISCRETE_MULTI: 2, # Sensor has multiple discrete readings
}


@dataclass(kw_only=True)
class RaritanSensor(RaritanUpdatable):
    """Representation of a generic device sensor."""

    unit: str | None = None
    last_reset: datetime | None = None
    available: bool | None = None
    last_sample: datetime | None = None

    @property
    def value(self) -> Any:
        raise NotImplementedError


@dataclass(kw_only=True)
class RaritanStateSensor(RaritanSensor):
    """Representation of a device state sensor."""

    source: StateSensor
    state: RaritanSensorState | None = None
    last_reset: None = None
    unit: None = None
    type: Any = None

    @property
    def value(self) -> str | None:
        return self.state.friendly_name() if self.state is not None else None

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        return [
            ((self.source.getTypeSpec, []), self.update_type),
        ]

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return [
            ((self.source.getState, []), self.update_state),
        ]

    def update_state(self, state: StateSensor.State) -> None:
        if (self.type):
            self.state = STATE_SENSOR_TYPE_VALUE_MAPPING[self.type][state.value]
            self.available = state.available
            self.last_sample = state.timestamp

    def update_type(self, spec: StateSensor.TypeSpec) -> None:
        if (spec.type in STATE_SENSOR_TYPE_MAPPING):
            self.type = STATE_SENSOR_TYPE_MAPPING[spec.type]


@dataclass(kw_only=True)
class RaritanSwitch(RaritanStateSensor):
    """Representation of a device switch."""

    state: OnOff | None = None


@dataclass(kw_only=True)
class RaritanNumericSensor(RaritanSensor):
    """Representation of a device numeric sensor."""

    source: NumericSensor
    reading: float | None = None

    @property
    def value(self) -> Any:
        return self.reading

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        return [
            ((self.source.getMetaData, []), self.update_metadata),
        ]

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return [
            ((self.source.getReading, []), self.update_reading),
        ]

    def update_reading(self, reading: NumericSensor.Reading) -> None:
        self.reading = reading.value

    def update_metadata(self, reading: NumericSensor.MetaData) -> None:
        if (reading.type.unit in SENSOR_UNITS_MAPPING):
            self.unit = SENSOR_UNITS_MAPPING[reading.type.unit]


@dataclass(kw_only=True)
class RaritanAccumulatingSensor(RaritanNumericSensor):
    """Representation of a device accumulating numeric sensor."""

    source: AccumulatingNumericSensor

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return super().update_readings() + [
            ((self.source.getLastResetTime, []), self.update_reset),
        ]

    def update_reset(self, last_reset: Time) -> None:
        self.last_reset = last_reset


@dataclass(kw_only=True)
class RaritanMultiSensor(RaritanSensor):

    sensors: list[RaritanSensor]

    @classmethod
    def from_sensor_sources(cls, sources: dict[str, Sensor | None]) -> Self:
        types = get_type_hints(cls)
        sensor_type = get_args(types['sensors'])[0]

        return cls(sensors=[sensor_type(source=src) for src in sources])

    @property
    def value(self) -> Any:
        return self.sensors[0].value if len(self.sensors) else None

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        return list(chain.from_iterable([
            sensor.update_info() for sensor in self.sensors
        ]))

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return list(chain.from_iterable([
            sensor.update_readings() for sensor in self.sensors
        ]))


@dataclass(kw_only=True)
class RaritanMultiStateSensor(RaritanMultiSensor):

    sensors: list[RaritanStateSensor]
