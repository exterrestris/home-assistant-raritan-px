"""Raritan PX services."""

import logging
from typing import TYPE_CHECKING

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    callback,
)
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.raritan_px.const import DOMAIN
from custom_components.raritan_px.firmware import FirmwareCatalogueError, FirmwareDownloadError, FirmwareManagerError
from custom_components.raritan_px.firmware.const import CATALOGUE_MANAGER

if TYPE_CHECKING:
    from custom_components.raritan_px.coordinator import RaritanPduConfigEntry
    from custom_components.raritan_px.firmware import FirmwareManager

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions for the Raritan PX integration."""

    async def async_update_catalogue(call: ServiceCall) -> None:  # noqa: ARG001
        """Update the firmware catalogue."""
        manager: FirmwareManager = hass.data[CATALOGUE_MANAGER]

        try:
            await manager.get_catalogue(force_update=True)

            config_entry: RaritanPduConfigEntry

            for config_entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False):
                if config_entry.runtime_data:
                    # Disable the catalogue update check as we've just updated the catalogue
                    config_entry.runtime_data.firmware_coordinator.catalogue_update_check = False

                    try:
                        await config_entry.runtime_data.firmware_coordinator.async_request_refresh()
                    except UpdateFailed:
                        _LOGGER.warning("Unable to refresh coordinator", exc_info=True)

                    # Reenable the catalogue update check for future refreshes
                    config_entry.runtime_data.firmware_coordinator.catalogue_update_check = True
        except FirmwareCatalogueError:
            _LOGGER.exception("Unable to update firmware catalogue")

    async def async_download_latest_firmware(call: ServiceCall) -> None:  # noqa: ARG001
        """Download the latest firmare for all configured PDUs."""
        manager: FirmwareManager = hass.data[CATALOGUE_MANAGER]

        try:
            catalogue = await manager.get_catalogue(force_update=True)

            config_entry: RaritanPduConfigEntry

            for config_entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False):
                if config_entry.runtime_data:
                    try:
                        firmware = catalogue.get_latest_firmware(
                            config_entry.runtime_data.pdu.model, config_entry.runtime_data.pdu.firmware_version
                        )

                        if firmware:
                            await manager.download_firmware(firmware)
                    except FirmwareDownloadError:
                        _LOGGER.warning("Unable to downloade firmware", exc_info=True)
        except FirmwareCatalogueError:
            _LOGGER.exception("Unable to update firmware catalogue")

    hass.services.async_register(DOMAIN, "update_firmware_catalogue", async_update_catalogue)

    async_register_admin_service(hass, DOMAIN, "download_latest_firmware", async_download_latest_firmware)
