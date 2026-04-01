"""Support for RaritanPdu sensor entities."""

from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.raritan_px.entity.sensor.description import (
    RaritanPduSensorEntityDescription,
    RaritanPduInletSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
    RaritanPduOverCurrentProtectorSensorEntityDescription,
)
from custom_components.raritan_px.entity.sensor import (
    RaritanPduSensorEntity,
    RaritanPduOutletSensorEntity,
    RaritanPduInletSensorEntity,
    RaritanPduOverCurrentProtectorSensorEntity,
)
from custom_components.raritan_px.api.model.device import RaritanPdu
from custom_components.raritan_px.coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from custom_components.raritan_px.entity.sensor.sensors import get_entity_description

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

    async_add_entities(
        RaritanPduOverCurrentProtectorSensorEntity(
            ocp,
            pdu,
            coordinator,
            get_entity_description(RaritanPduOverCurrentProtectorSensorEntityDescription, sensor_name, sensor),
            sensor
        )
        for ocp in pdu.ocps
        for (sensor_name, sensor) in ocp.available_sensors
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
