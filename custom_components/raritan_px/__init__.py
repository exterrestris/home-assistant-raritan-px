"""Raritan PX2/PX3 PDU Integration."""

import asyncio
from collections.abc import Iterable
from datetime import timedelta
import logging
from typing import Any, cast
from homeassistant.const import (
    CONF_ALIAS,
    CONF_AUTHENTICATION,
    CONF_HOST,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
)

from .const import (
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)

from .api import (
    RaritanClient,
    AuthenticationDetails,
    ConnectionDetails,
    AuthenticationError,
    RaritanClientError,
    RaritanPdu,
)


DISCOVERY_INTERVAL = timedelta(minutes=15)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Set up RaritanPdu from a config entry."""
    host: str = entry.data[CONF_HOST]
    credentials = await get_credentials(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Unload a config entry."""
    data = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok


async def get_credentials(hass: HomeAssistant) -> AuthenticationDetails | None:
    """Retrieve the credentials from hass data."""
    if DOMAIN in hass.data and CONF_AUTHENTICATION in hass.data[DOMAIN]:
        auth = hass.data[DOMAIN][CONF_AUTHENTICATION]
        return AuthenticationDetails(auth[CONF_USERNAME], auth[CONF_PASSWORD])

    return None


async def set_credentials(
    hass: HomeAssistant, credentials: AuthenticationDetails
) -> None:
    """Save the credentials to HASS data."""
    hass.data.setdefault(DOMAIN, {})[CONF_AUTHENTICATION] = {
        CONF_USERNAME: credentials.user,
        CONF_PASSWORD: credentials.passwd,
    }
