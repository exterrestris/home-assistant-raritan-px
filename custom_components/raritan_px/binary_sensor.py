"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.binary_sensor import (
    RaritanPduAttributeBackedBinarySensorEntity,
)
from custom_components.raritan_px.entity.binary_sensor.descriptions import (
    PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS,
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
        RaritanPduAttributeBackedBinarySensorEntity(
            pdu,
            data.hub,
            coordinator,
            desc,
        )
        for desc in PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS
    )
