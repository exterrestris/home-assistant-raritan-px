"""Support for RaritanPdu switch entities."""

from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.raritan_px.entity.switch import RaritanPduOutletSwitchEntity
from custom_components.raritan_px.entity.switch.description import RaritanPduOutletSwitchEntityDescription
from custom_components.raritan_px.entity.switch.switches import get_entity_description
from custom_components.raritan_px.api.model.device import RaritanPdu
from custom_components.raritan_px.coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
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
                switch
            )
            for outlet in pdu.outlets
            for (switch_name, switch) in outlet.available_switches
        )
