"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.sensor import (
    RaritanPduInletSensorEntity,
    RaritanPduOutletSensorEntity,
    RaritanPduSensorEntity,
)
from custom_components.raritan_px.entity.sensor.descriptions import (
    RaritanPduInletSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
    RaritanPduSensorEntityDescription,
    get_entity_description,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.coordinator import (
        RaritanPduConfigEntry,
        RaritanPduData,
        RaritanPduDataUpdateCoordinator,
    )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
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
            get_entity_description(RaritanPduSensorEntityDescription, sensor_name),
            sensor,
        )
        for sensor_name, sensor in pdu.available_sensors
    )

    async_add_entities(
        RaritanPduInletSensorEntity(
            inlet,
            pdu,
            coordinator,
            get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name),
            sensor,
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
                get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name),
                sensor,
            )
            for outlet in pdu.outlets
            for (sensor_name, sensor) in outlet.available_sensors
        )
