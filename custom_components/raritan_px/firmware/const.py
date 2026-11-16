"""Raritan firmware catalogue constants."""

from typing import TYPE_CHECKING, Final

from homeassistant.util.hass_dict import HassKey

if TYPE_CHECKING:
    from homeassistant.helpers.storage import Store

CATALOGUE_URL: Final[str] = "https://api.github.com/repos/exterrestris/ha-raritan-px-firmware/releases/latest"
CATALOGUE_FILE: Final[str] = "catalogue.json"

CATALOGUE_STORE: HassKey[Store] = HassKey("firmware_catalogue")

STORAGE_KEY: Final[str] = "raritan_px.firmware_catalogue"
STORAGE_VERSION: Final[int] = 1
