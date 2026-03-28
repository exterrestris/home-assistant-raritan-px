"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import RaritanClient
from .api.model.device import RaritanPdu

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    client: RaritanClient
    coordinator: RaritanPduDataUpdateCoordinator


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]

REQUEST_REFRESH_DELAY = 0.35


class RaritanPduDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """DataUpdateCoordinator to gather data for a specific RaritanPdu device."""

    config_entry: RaritanPduConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        config_entry: RaritanPduConfigEntry,
        update_interval: timedelta,
        client: RaritanClient,
        pdu: RaritanPdu,
    ) -> None:
        """Initialize the RaritanPdu coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name="RaritanPdu",
            update_interval=update_interval,
        )
        self.pdu = pdu
        self.client = client
        self.config_entry = config_entry


    async def _async_update_data(self) -> None:
        """Fetch all device and sensor data from api."""
        try:
            await self.client.update_pdu_sensors_data(self.pdu)
        except Exception as ex:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="device_error",
                translation_placeholders={
                    "func": "update_outlets",
                    "exc": str(ex),
                },
            ) from ex
