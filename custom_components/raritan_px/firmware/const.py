"""Raritan firmware catalogue constants."""

from typing import TYPE_CHECKING, Final

from homeassistant.util.hass_dict import HassKey

if TYPE_CHECKING:
    from homeassistant.helpers.storage import Store

    from custom_components.raritan_px.firmware import FirmwareManager

CATALOGUE_URL: Final[str] = "https://api.github.com/repos/exterrestris/ha-raritan-px-firmware/releases/latest"
CATALOGUE_FILE: Final[str] = "catalogue.json"

CATALOGUE_MANAGER: HassKey[FirmwareManager] = HassKey("firmware_catalogue_manager")
CATALOGUE_STORE: HassKey[Store] = HassKey("firmware_catalogue")

CATALOGUE_STORE_STORAGE_KEY: Final[str] = "raritan_px.firmware_catalogue"
CATALOGUE_STORE_STORAGE_VERSION: Final[int] = 1

FIRMWARE_DIR: Final[str] = "firmware"
FIRMWARE_SUFFIX: Final[str] = ".bin"

# Zip bomb protection limits. Typical firmware zip contains 1 ~16MB file
FIRMWARE_ZIP_MAX_FILES: Final[int] = 2
FIRMWARE_ZIP_MAX_SIZE: Final[int] = 32 * 1024 * 1024  # 32MB

DOWNLOAD_CHUNK: Final[int] = 16 * 1024  # 16kB
