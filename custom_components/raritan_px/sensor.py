"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.sensor import (
    RaritanIntegrationCoordinatorSensorEntity,
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
    INTEGRATION_COORDINATOR_ENTITY_DESCPRIPTIONS,
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

    from custom_components.raritan_px.coordinator import (
        RaritanPduConfigEntry,
        RaritanPduData,
    )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    data: RaritanPduData = config_entry.runtime_data

    async_add_entities(
        RaritanPduSensorBackedSensorEntity(
            data.api_coordinator,
            device=data.pdu,
            hub=data.hub,
            description=description,
            sensor=sensor,
        )
        for sensor_name, sensor in data.pdu.available_sensors
        if (description := get_entity_description(RaritanPduSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduAttributeBackedSensorEntity(data.api_coordinator, device=data.pdu, hub=data.hub, description=desc)
        for desc in PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(data.pdu)
    )

    async_add_entities(
        RaritanPduAttributeBackedSensorEntity(
            data.api_coordinator, device=data.pdu, hub=data.hub, description=desc(key, interface)
        )
        for (key, interface) in data.pdu.network_interfaces.items()
        for desc in PDU_NETWORK_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduInletSensorBackedSensorEntity(
            data.api_coordinator,
            device=inlet,
            hub=data.hub,
            description=description,
            sensor=sensor,
        )
        for (_, inlet) in data.pdu.inlets.items()
        for (sensor_name, sensor) in inlet.available_sensors
        if (description := get_entity_description(RaritanPduInletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduInletAttributeBackedSensorEntity(data.api_coordinator, device=inlet, hub=data.hub, description=desc)
        for (_, inlet) in data.pdu.inlets.items()
        for desc in INLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(inlet)
    )

    async_add_entities(
        RaritanPduOutletSensorBackedSensorEntity(
            data.api_coordinator,
            device=outlet,
            hub=data.hub,
            description=description,
            sensor=sensor,
        )
        for (_, outlet) in data.pdu.outlets.items()
        for (sensor_name, sensor) in outlet.available_sensors
        if (description := get_entity_description(RaritanPduOutletSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOutletAttributeBackedSensorEntity(data.api_coordinator, device=outlet, hub=data.hub, description=desc)
        for (_, outlet) in data.pdu.outlets.items()
        for desc in OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(outlet)
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorSensorBackedSensorEntity(
            data.api_coordinator,
            device=ocp,
            hub=data.hub,
            description=description,
            sensor=sensor,
        )
        for (_, ocp) in data.pdu.ocps.items()
        for (sensor_name, sensor) in ocp.available_sensors
        if (description := get_entity_description(RaritanPduOverCurrentProtectorSensorEntityDescription, sensor_name))
    )

    async_add_entities(
        RaritanPduOverCurrentProtectorAttributeBackedSensorEntity(
            data.api_coordinator, device=ocp, hub=data.hub, description=desc
        )
        for (_, ocp) in data.pdu.ocps.items()
        for desc in OVERCURRENT_PROTECTOR_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(ocp)
    )

    async_add_entities(
        RaritanIntegrationCoordinatorSensorEntity(data.firmware_coordinator, description=desc, device=None, hub=None)
        for desc in INTEGRATION_COORDINATOR_ENTITY_DESCPRIPTIONS
    )
