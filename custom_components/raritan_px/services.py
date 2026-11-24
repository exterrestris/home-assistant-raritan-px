"""Raritan PX services."""

import logging
from typing import TYPE_CHECKING, Any, Final

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    SupportsResponse,
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
    from custom_components.raritan_px.firmware.model import Firmware

_LOGGER = logging.getLogger(__name__)

_GET_AVAILABLE_FIRMWARE_ARGS_VERBOSE: Final[str] = "verbose"
_GET_AVAILABLE_FIRMWARE_ARGS_INC_CURRENT: Final[str] = "current"
_GET_AVAILABLE_FIRMWARE_SCHEMA: Final[vol.Schema] = vol.Schema(
    {
        vol.Required(_GET_AVAILABLE_FIRMWARE_ARGS_VERBOSE): bool,
        vol.Required(_GET_AVAILABLE_FIRMWARE_ARGS_INC_CURRENT): bool,
    }
)


async def _async_update_catalogue(call: ServiceCall) -> None:
    """Update the firmware catalogue."""
    manager: FirmwareManager = call.hass.data[CATALOGUE_MANAGER]

    try:
        await manager.get_catalogue(force_update=True)

        config_entry: RaritanPduConfigEntry

        for config_entry in call.hass.config_entries.async_entries(DOMAIN, include_ignore=False):
            if config_entry.runtime_data:
                # Get the current catalogue update check setting and then disable it as we've just updated the catalogue
                catalogue_update_check = config_entry.runtime_data.firmware_coordinator.catalogue_update_check
                config_entry.runtime_data.firmware_coordinator.catalogue_update_check = False

                try:
                    await config_entry.runtime_data.firmware_coordinator.async_request_refresh()
                except UpdateFailed:
                    _LOGGER.warning("Unable to refresh coordinator", exc_info=True)

                # Reenable the catalogue update check for future refreshes
                config_entry.runtime_data.firmware_coordinator.catalogue_update_check = catalogue_update_check
    except FirmwareCatalogueError:
        _LOGGER.exception("Unable to update firmware catalogue")


async def _async_get_catalogue(call: ServiceCall) -> dict[str, Any]:
    """Update the firmware catalogue."""
    manager: FirmwareManager = call.hass.data[CATALOGUE_MANAGER]

    catalogue = await manager.get_catalogue()

    return catalogue.model_dump(mode="json")


async def _async_get_available_firmware(call: ServiceCall) -> dict[str, Any]:
    """Return the forecast for the coming days."""

    def format_fw(firmware: Firmware) -> str | dict[str, Any]:
        if call.data.get(_GET_AVAILABLE_FIRMWARE_ARGS_VERBOSE):
            return firmware.model_dump(mode="json")

        return str(firmware.version)

    manager: FirmwareManager = call.hass.data[CATALOGUE_MANAGER]

    catalogue = await manager.get_catalogue()

    data = {"catalogue": str(catalogue.version), "devices": {}}

    config_entry: RaritanPduConfigEntry

    for config_entry in call.hass.config_entries.async_entries(DOMAIN, include_ignore=False):
        if config_entry.runtime_data:
            pdu = config_entry.runtime_data.pdu

            firmwares = catalogue.get_available_firmware(
                pdu.model,
                current_firmware=pdu.firmware_version,
                include_current=call.data.get(_GET_AVAILABLE_FIRMWARE_ARGS_INC_CURRENT, True),
            )

            data["devices"][pdu.device_name] = {
                "model": pdu.model,
                "current": pdu.firmware_version,
                "firmwares": [format_fw(fw) for fw in firmwares],
            }

    return data


async def _async_download_latest_firmware(call: ServiceCall) -> None:
    """Download the latest firmare for all configured PDUs."""
    manager: FirmwareManager = call.hass.data[CATALOGUE_MANAGER]

    try:
        catalogue = await manager.get_catalogue(force_update=True)

        config_entry: RaritanPduConfigEntry

        for config_entry in call.hass.config_entries.async_entries(DOMAIN, include_ignore=False):
            if config_entry.runtime_data:
                try:
                    firmware = catalogue.get_latest_firmware(
                        config_entry.runtime_data.pdu.model,
                        current_firmware=config_entry.runtime_data.pdu.firmware_version,
                        include_current=False,
                    )

                    if firmware:
                        await manager.download_firmware(firmware)
                except FirmwareDownloadError:
                    _LOGGER.warning("Unable to downloade firmware", exc_info=True)
    except FirmwareCatalogueError:
        _LOGGER.exception("Unable to update firmware catalogue")


async def _async_clear_firmware_downloads(call: ServiceCall) -> None:
    """Clear all downloaded firmware zip/binary files."""
    manager: FirmwareManager = call.hass.data[CATALOGUE_MANAGER]

    try:
        await manager.clear_downloaded_firmware()
    except FirmwareManagerError:
        _LOGGER.exception("Unable to clear downloaded firmware")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions for the Raritan PX integration."""
    hass.services.async_register(DOMAIN, "update_firmware_catalogue", _async_update_catalogue)

    async_register_admin_service(
        hass, DOMAIN, "get_firmware_catalogue", _async_get_catalogue, supports_response=SupportsResponse.ONLY
    )

    async_register_admin_service(
        hass,
        DOMAIN,
        "get_available_firmware",
        _async_get_available_firmware,
        _GET_AVAILABLE_FIRMWARE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async_register_admin_service(hass, DOMAIN, "download_latest_firmware", _async_download_latest_firmware)

    async_register_admin_service(hass, DOMAIN, "clear_downloaded_firmware", _async_clear_firmware_downloads)
