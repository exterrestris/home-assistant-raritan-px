from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

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
from raritan.rpc import Interface as RpcInterface
from raritan.rpc.sensors import AccumulatingNumericSensor, NumericSensor, Sensor, StateSensor

from . import RaritanUpdatable


SENSOR_UNITS_MAPPING = {
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


@dataclass
class RaritanSensor(RaritanUpdatable):
    """Representation of a generic device sensor."""

    source: Sensor
    unit: None = None

    @property
    def value(self) -> Any:
        raise NotImplementedError


@dataclass
class RaritanStateSensor(RaritanSensor):
    """Representation of a device state sensor."""

    source: StateSensor
    state: Any = None

    @property
    def value(self) -> Any:
        return self.state

    def update_methods(self) -> list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[StateSensor.State], None]]]:
        return [
            ((self.source.getState, []), self.update_state),
        ]

    def update_state(self, state: StateSensor.State) -> None:
        self.state = state.value


@dataclass
class RaritanNumericSensor(RaritanSensor):
    """Representation of a device numeric sensor."""

    source: NumericSensor
    reading: float | None = None
    unit: Any | None = None

    @property
    def value(self) -> Any:
        return self.reading

    def update_methods(self) -> list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[Any], None]]]:
        return [
            ((self.source.getReading, []), self.update_reading),
            ((self.source.getMetaData, []), self.update_metadata),
        ]

    def update_reading(self, reading: NumericSensor.Reading) -> None:
        self.reading = reading.value

    def update_metadata(self, reading: NumericSensor.MetaData) -> None:
        if (reading.type.unit in SENSOR_UNITS_MAPPING):
            self.unit = SENSOR_UNITS_MAPPING[reading.type.unit]


@dataclass
class RaritanAccumulatingSensor(RaritanNumericSensor):
    """Representation of a device accumulating numeric sensor."""

    source: AccumulatingNumericSensor
    last_reset: datetime | None = None
