"""Support for RaritanPdu sensor entities."""

from __future__ import annotations
from typing import TypeVar, Any
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from itertools import product
from more_itertools import flatten
from dataclasses import dataclass, asdict
import logging
from homeassistant.const import DEGREE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from .api.model.device import (
    RaritanPduDevice,
    RaritanPduInlet,
    RaritanPduOutlet,
    RaritanPdu,
)
from .api.model.sensor import RaritanSensor
from .api.model.sensor.states import NormalAlarmed, OkFaulted, ResidualCurrentStatus
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from .entity import (
    CoordinatedRaritanPduDeviceEntity,
    RaritanPduDeviceEntityDescription,
    RaritanPduEntityDescription,
    RaritanPduOutletEntityDescription,
    RaritanPduInletEntityDescription,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduInletEntity,
)

type SensorEntityValue = StateType | date | datetime | Decimal

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceSensorEntityDescription(
    SensorEntityDescription, RaritanPduDeviceEntityDescription
):
    """Base class for a Raritan PDU device sensor entity description."""

    convert_fn: Callable[[Any], SensorEntityValue | None] | None = None

@dataclass(frozen=True, kw_only=True)
class RaritanPduSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduEntityDescription
):
    """Base class for a Raritan PDU sensor entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduInletSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduInletEntityDescription
):
    """Base class for a Raritan PDU inlet sensor entity description."""


SENSOR_DESCRIPTIONS: tuple[RaritanPduDeviceSensorEntityDescription, ...] = (
    #region PDU Sensors
    RaritanPduSensorEntityDescription(
        key="power_supply_status",
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        name="Power Supply {} Status"
    ),
    RaritanPduSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    RaritanPduSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        name="Apparent Energy",
    ),
    #endregion
    #region Outlet Sensors
    RaritanPduOutletSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Peak Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="maximum_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Maximum Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="unbalanced_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="displacement_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        name="Displacement Power Factor",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        name="Apparent Energy",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="phase_angle",
        state_class=SensorStateClass.MEASUREMENT,
        name="Phase Angle",
        native_unit_of_measurement=DEGREE,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="line_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        name="Line Frequency",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="crest_factor",
        state_class=SensorStateClass.MEASUREMENT,
        name="Crest Factor",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="voltage_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="current_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="inrush_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Inrush Current",
    ),
    #endregion
    #region Inlet Sensors
    RaritanPduInletSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Peak Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_ac_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual AC Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_dc_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual DC Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="displacement_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        name="Displacement Power Factor",
    ),
    RaritanPduInletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        name="Apparent Energy",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_line_line_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Line-Line Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Voltage",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_line_line_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Line-Line Voltage",
    ),
    RaritanPduInletSensorEntityDescription(
        key="line_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="phase_angle",
        state_class=SensorStateClass.MEASUREMENT,
        name="Phase Angle",
        native_unit_of_measurement=DEGREE,
    ),
    RaritanPduInletSensorEntityDescription(
        key="crest_factor",
        state_class=SensorStateClass.MEASUREMENT,
        name="Crest Factor",
    ),
    RaritanPduInletSensorEntityDescription(
        key="voltage_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduInletSensorEntityDescription(
        key="current_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduInletSensorEntityDescription(
        key="power_quality",
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        name="Power_Quality",
    ),
    RaritanPduInletSensorEntityDescription(
        key="surge_protector_status",
        device_class=SensorDeviceClass.ENUM,
        options=OkFaulted.options(),
        name="Surge Protector Status",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual current status",
        device_class=SensorDeviceClass.ENUM,
        options=ResidualCurrentStatus.options(),
        name="Residual Current Status",
    ),
    #endregion
)

SENSOR_DESCRIPTIONS_MAP = { (type(desc), desc.key) : desc for desc in SENSOR_DESCRIPTIONS}

T = TypeVar('T', bound="RaritanPduDeviceSensorEntityDescription", covariant=True)

def get_entity_description(desc_type: type[T], sensor_name: str, sensor: RaritanSensor) -> T:
    def default_name(name: str = sensor_name) -> str:
        return name.replace('_', ' ').replace(':', ' ').title()

    if (desc_type, sensor_name) in SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_DESCRIPTIONS_MAP[(desc_type, sensor_name)] # pyright: ignore[reportReturnType, reportArgumentType]

    if ':' in sensor_name:
        generic_name, idx = sensor_name.split(':')

        if (desc_type, generic_name) in SENSOR_DESCRIPTIONS_MAP:
            desc = SENSOR_DESCRIPTIONS_MAP[(desc_type, generic_name)] # pyright: ignore[reportArgumentType]

            def formatted_name():
                if type(desc.name) is str:
                    return desc.name.format(int(idx) + 1)

                return f"{default_name(generic_name)} {int(idx) + 1}"

            return desc_type(
                **(asdict(desc) | {
                    'key': sensor_name,
                    'name': formatted_name(),
                })
            )

    return desc_type(
        key = sensor_name,
        name = default_name(),
    )

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    async_add_entities(
        RaritanPduSensorEntity(
            pdu,
            pdu,
            coordinator,
            get_entity_description(RaritanPduSensorEntityDescription, sensor_name, sensor),
            sensor
        )
        for sensor_name, sensor in pdu.available_sensors
    )

    async_add_entities(
        RaritanPduInletSensorEntity(
            inlet,
            pdu,
            coordinator,
            get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name, sensor),
            sensor
        )
        for inlet in pdu.inlets
        for (sensor_name, sensor) in inlet.available_sensors
    )

    if pdu.has_metered_outlets:
        async_add_entities(
            RaritanPduOutletSensorEntity(
                outlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name, sensor),
                sensor
            )
            for outlet in pdu.outlets
            for (sensor_name, sensor) in outlet.available_sensors
        )

class RaritanPduDeviceSensorEntity(CoordinatedRaritanPduDeviceEntity, SensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _sensor: RaritanSensor
    entity_description: RaritanPduDeviceSensorEntityDescription

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceEntityDescription,
            sensor: RaritanSensor
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._sensor = sensor

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._sensor.value

        if value is not None:
            if self.entity_description.convert_fn is not None:
                value = self.entity_description.convert_fn(value)

            if self._sensor.precision is not None:
                self._attr_suggested_display_precision = self._sensor.precision

        self._attr_native_value = value

        # This check is here because Home Assistant only supports last_reset with a
        # state class of TOTAL, however the Raritan JSON-RPC API only supplies a last
        # reset time for accumlating numeric sensors which best map to a state class
        # of TOTAL_INCREASING
        if self.entity_description.state_class == SensorStateClass.TOTAL:
            if self._sensor.last_reset is not None:
                self._attr_last_reset = self._sensor.last_reset

        if self._sensor.unit is not None:
            self._attr_native_unit_of_measurement = self._sensor.unit

        return True


class RaritanPduSensorEntity(CoordinatedRaritanPduEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPdu
    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOutletSensorEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduInletSensorEntity(CoordinatedRaritanPduInletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Inlet switch."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletSensorEntityDescription
