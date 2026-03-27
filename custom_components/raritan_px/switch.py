"""Support for RaritanPdu switch entities."""

from __future__ import annotations
from typing import Any
from dataclasses import dataclass
import logging
from homeassistant.core import HomeAssistant, callback

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from .entity import RaritanPduEntityDescription, CoordinatedRaritanPduOutletEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSwitchEntityDescription(
    SwitchEntityDescription, RaritanPduEntityDescription
):
    """Base class for a Raritan PDU outlet switch entity description."""


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
        pass


class RaritanPduOutletSwitchEntity(CoordinatedRaritanPduOutletEntity, SwitchEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSwitchEntityDescription

    # @async_refresh_after
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""

    # @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""

        return True
