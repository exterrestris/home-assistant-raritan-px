"""Support for RaritanPdu switch entities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from .api import RaritanPdu, RaritanPduOutlet
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from .entity import RaritanPduEntityDescription, CoordinatedRaritanPduOutletEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSensorEntityDescription(
    SensorEntityDescription, RaritanPduEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    if pdu.has_metered_outlets:
        pass


class RaritanPduOutletSensorEntity(CoordinatedRaritanPduOutletEntity, SensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        return True
