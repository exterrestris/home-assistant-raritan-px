"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.binary_sensor import (
    RaritanPduAttributeBackedBinarySensorEntity,
    RaritanPduOutletAttributeBackedBinarySensorEntity,
)
from custom_components.raritan_px.entity.binary_sensor.descriptions import (
    OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
    PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
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
        RaritanPduAttributeBackedBinarySensorEntity(
            data.api_coordinator,
            hub=data.hub,
            description=desc,
            device=data.pdu,
        )
        for desc in PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )

    async_add_entities(
        RaritanPduOutletAttributeBackedBinarySensorEntity(
            data.api_coordinator,
            device=outlet,
            hub=data.hub,
            description=desc
        )
        for (_, outlet) in data.pdu.outlets.items()
        for desc in OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
        if desc.is_available_for(outlet)
    )
