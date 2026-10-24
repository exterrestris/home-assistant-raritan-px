"""Support for RaritanPdu switch entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.raritan_px.entity.switch import RaritanPduOutletSwitchEntity
from custom_components.raritan_px.entity.switch.descriptions import (
    RaritanPduOutletSwitchEntityDescription,
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
    """Set up switches."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    if pdu.has_switchable_outlets:
        async_add_entities(
            RaritanPduOutletSwitchEntity(
                outlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduOutletSwitchEntityDescription, switch_name),
                switch,
            )
            for outlet in pdu.outlets
            for (switch_name, switch) in outlet.available_switches
        )
