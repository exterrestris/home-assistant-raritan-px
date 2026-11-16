"""Support for RaritanPdu sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.coordinator import RaritanFirmwareDataUpdateCoordinator
from custom_components.raritan_px.entity.update import PDU_FIRMWARE_UPDATE_DESCRIPTION, RaritanPduFirmwareUpdateEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.coordinator import (
        RaritanFirmwareDataUpdateCoordinator,
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
    coordinator: RaritanFirmwareDataUpdateCoordinator = data.firmware_coordinator
    pdu: RaritanPdu = data.api_coordinator.pdu

    async_add_entities(
        [
            RaritanPduFirmwareUpdateEntity(
                pdu,
                data.hub,
                coordinator,
                PDU_FIRMWARE_UPDATE_DESCRIPTION,
            )
        ]
    )
