"""Support for RaritanPdu sensor entities."""

from __future__ import annotations
import logging
from itertools import chain
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.raritan_px.entity.sensor.description import (
    RaritanPduSensorEntityDescription,
    RaritanPduInletSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription
)
from custom_components.raritan_px.entity.sensor import (
    RaritanPduSensorBackedSensorEntity,
    RaritanPduOutletSensorBackedSensorEntity,
    RaritanPduInletSensorBackedSensorEntity,
    RaritanPduOutletPropertyBackedSensorEntity,
    RaritanPduInletPropertyBackedSensorEntity,
)
from custom_components.raritan_px.api.model.device import RaritanPdu
from custom_components.raritan_px.coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from custom_components.raritan_px.entity.sensor.sensors import (
    get_entity_description,
    INLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS,
    OUTLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    async_add_entities(chain(
        (
            RaritanPduSensorBackedSensorEntity(
                pdu,
                pdu,
                coordinator,
                get_entity_description(RaritanPduSensorEntityDescription, sensor_name, sensor),
                sensor
            )
            for sensor_name, sensor in pdu.available_sensors
        ), (
            RaritanPduInletSensorBackedSensorEntity(
                inlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name, sensor),
                sensor
            )
            for inlet in pdu.inlets
            for (sensor_name, sensor) in inlet.available_sensors
        ), (
            RaritanPduInletPropertyBackedSensorEntity(
                inlet,
                pdu,
                coordinator,
                desc,
                desc.key
            )
            for inlet in pdu.inlets for desc in INLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS
        ), (
            RaritanPduOutletSensorBackedSensorEntity(
                outlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name, sensor),
                sensor
            )
            for outlet in pdu.outlets
            for (sensor_name, sensor) in outlet.available_sensors
        ), (
            RaritanPduOutletPropertyBackedSensorEntity(
                outlet,
                pdu,
                coordinator,
                desc,
                desc.key
            )
            for outlet in pdu.outlets for desc in OUTLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS
        )
    ))
