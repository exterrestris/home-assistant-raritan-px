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
    PDU_NETWORK_ENTITY_DESCRIPTIONS,
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
    pdu: RaritanPdu = data.coordinator.pdu

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
        RaritanPduAttributeBackedSensorEntity(pdu, data.hub, data.coordinator, desc)
        for desc in PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(pdu)
    )

    async_add_entities(
        RaritanPduAttributeBackedSensorEntity(pdu, data.hub, data.coordinator, desc(key, interface))
        for (key, interface) in pdu.network_interfaces.items()
        for desc in PDU_NETWORK_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduInletSensorBackedSensorEntity(
            inlet,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for (_, inlet) in pdu.inlets.items()
        for (sensor_name, sensor) in inlet.available_sensors
        if (description := get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduInletAttributeBackedSensorEntity(inlet, data.hub, data.coordinator, desc)
        for (_, inlet) in pdu.inlets.items()
        for desc in INLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(inlet)
    )

    async_add_entities(
        RaritanPduOutletSensorBackedSensorEntity(
            outlet,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for (_, outlet) in pdu.outlets.items()
        for (sensor_name, sensor) in outlet.available_sensors
        if (description := get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOutletAttributeBackedSensorEntity(outlet, data.hub, data.coordinator, desc)
        for (_, outlet) in pdu.outlets.items()
        for desc in OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(outlet)
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorSensorBackedSensorEntity(
            ocp,
            data.hub,
            coordinator,
            description,
            sensor,
        )
        for (_, ocp) in pdu.ocps.items()
        for (sensor_name, sensor) in ocp.available_sensors
        if (description := get_entity_description(RaritanPduOverCurrentProtectorSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorAttributeBackedSensorEntity(ocp, data.hub, data.coordinator, desc)
        for (_, ocp) in pdu.ocps.items()
        for desc in OVERCURRENT_PROTECTOR_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(ocp)
    )
