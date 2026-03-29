"""Support for RaritanPdu sensor entities."""

from __future__ import annotations
from typing import TypeVar
from itertools import product
from more_itertools import flatten
from dataclasses import dataclass, asdict
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
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
from .api.model.sensor.states import NormalAlarmed
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

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceSensorEntityDescription(
    SensorEntityDescription, RaritanPduDeviceEntityDescription
):
    """Base class for a Raritan PDU device sensor entity description."""

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
    RaritanPduSensorEntityDescription(
        key="power_supply_status",
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        name="Power Supply {} Status"
    ),
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
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
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
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
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
        for inlet, (sensor_name, sensor) in list(
            flatten([list(product([inlet], sensors)) for (inlet, sensors) in [(inlet, inlet.available_sensors) for inlet in pdu.inlets]])
        )
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
            for outlet, (sensor_name, sensor) in list(
                flatten([list(product([outlet], sensors)) for (outlet, sensors) in [(outlet, outlet.available_sensors) for outlet in pdu.outlets]])
            )
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

        self._attr_native_value = value

        if (self._sensor.unit) is not None:
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
