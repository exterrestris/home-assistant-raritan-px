"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.sensor import (
    RaritanPduAttributeBackedSensorEntity,
    RaritanPduInletAttributeBackedSensorEntity,
    RaritanPduInletSensorBackedSensorEntity,
    RaritanPduOutletAttributeBackedSensorEntity,
    RaritanPduOutletSensorBackedSensorEntity,
    RaritanPduOverCurrentProtectorAttributeBackedSensorEntity,
    RaritanPduOverCurrentProtectorSensorBackedSensorEntity,
    RaritanPduSensorBackedSensorEntity,
)
from custom_components.raritan_px.entity.sensor.descriptions import (
    INLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
    OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
    OVERCURRENT_PROTECTOR_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
    PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
    RaritanPduInletSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
    RaritanPduOverCurrentProtectorSensorEntityDescription,
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
        RaritanPduSensorBackedSensorEntity(
            pdu,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for sensor_name, sensor in pdu.available_sensors
        if (description := get_entity_description(RaritanPduSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduAttributeBackedSensorEntity(pdu, data.hub, coordinator, desc, desc.key)
        for desc in PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduInletSensorBackedSensorEntity(
            inlet,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for inlet in pdu.inlets
        for (sensor_name, sensor) in inlet.available_sensors
        if (description := get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduInletAttributeBackedSensorEntity(inlet, data.hub, coordinator, desc, desc.key)
        for inlet in pdu.inlets
        for desc in INLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduOutletSensorBackedSensorEntity(
            outlet,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for outlet in pdu.outlets
        for (sensor_name, sensor) in outlet.available_sensors
        if (description := get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOutletAttributeBackedSensorEntity(outlet, data.hub, coordinator, desc, desc.key)
        for outlet in pdu.outlets
        for desc in OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorSensorBackedSensorEntity(
            ocp,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for ocp in pdu.ocps
        for (sensor_name, sensor) in ocp.available_sensors
        if (description := get_entity_description(RaritanPduOverCurrentProtectorSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorAttributeBackedSensorEntity(ocp, data.hub, coordinator, desc, desc.key)
        for ocp in pdu.ocps
        for desc in OVERCURRENT_PROTECTOR_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )
