"""Support for RaritanPdu sensor entities."""

from __future__ import annotations
from typing import TypeVar
from itertools import product
from more_itertools import flatten
from dataclasses import dataclass
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

def get_entity_description(type: type[T], key: str) -> T:
    if (type, key) in SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_DESCRIPTIONS_MAP[(type, key)] # pyright: ignore[reportReturnType, reportArgumentType]

    return type(
        key=key,
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
        RaritanPduInletSensorEntity(
            inlet,
            pdu,
            coordinator,
            get_entity_description(RaritanPduInletSensorEntityDescription, sensor),
        )
        for inlet, sensor in list(
            flatten([list(product([inlet], sensors)) for (inlet, sensors) in [(inlet, [sensor for sensor, _ in inlet.available_sensors]) for inlet in pdu.inlets]])
        )
    )

    if pdu.has_metered_outlets:
        async_add_entities(
            RaritanPduOutletSensorEntity(
                outlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduOutletSensorEntityDescription, sensor),
            )
            for outlet, sensor in list(
                flatten([list(product([outlet], sensors)) for (outlet, sensors) in [(outlet, [sensor for sensor, _ in outlet.available_sensors]) for outlet in pdu.outlets]])
            )
        )

class RaritanPduDeviceSensorEntity(CoordinatedRaritanPduDeviceEntity, SensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _sensor: RaritanSensor
    entity_description: RaritanPduDeviceSensorEntityDescription

    def __init__(self, device: RaritanPduDevice, pdu: RaritanPdu, coordinator: RaritanPduDataUpdateCoordinator, description: RaritanPduDeviceEntityDescription) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._sensor = self._device.sensors[self.entity_description.key]

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._sensor.value

        self._attr_native_value = value

        if (self._sensor.unit) is not None:
            self._attr_native_unit_of_measurement = self._sensor.unit

        return True


class RaritanPduOutletSensorEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduInletSensorEntity(CoordinatedRaritanPduInletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Inlet switch."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletSensorEntityDescription
