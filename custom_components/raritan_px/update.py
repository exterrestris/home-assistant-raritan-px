"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.update import PDU_FIRMWARE_UPDATE_DESCRIPTION, RaritanPduFirmwareUpdateEntity

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
        [
            RaritanPduFirmwareUpdateEntity(
                data.firmware_coordinator,
                device=data.api_coordinator.pdu,
                hub=data.hub,
                description=PDU_FIRMWARE_UPDATE_DESCRIPTION,
            )
        ]
    )
