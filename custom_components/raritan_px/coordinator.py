"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.raritan_px.api import RaritanPdu

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    parent_coordinator: RaritanPduDataUpdateCoordinator


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]

REQUEST_REFRESH_DELAY = 0.35


class RaritanPduDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """DataUpdateCoordinator to gather data for a specific RaritanPdu device."""

    config_entry: RaritanPduConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        pdu: RaritanPdu,
        update_interval: timedelta,
        config_entry: RaritanPduConfigEntry,
    ) -> None:
        """Initialize DataUpdateCoordinator to gather data for specific SmartPlug."""
    async def _async_update_data(self) -> None:
        """Fetch all device and sensor data from api."""
