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
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
)

from custom_components.raritan_px.api.model.device import RaritanPdu
from custom_components.raritan_px.api.client import (
    RaritanClient,
    AuthenticationDetails,
    ConnectionDetails,
    ConfigError as ClientConfigError,
    AuthenticationError,
    CertificateVerificationError,
    RaritanClientError,
)
from custom_components.raritan_px.api.const import (
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
)
from custom_components.raritan_px.const import (
    DOMAIN,
    PLATFORMS,
    CONF_CONFIG_ENTRY_MINOR_VERSION,
    UPDATE_INTERVAL,
)
from custom_components.raritan_px.coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)


DISCOVERY_INTERVAL = timedelta(minutes=15)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Set up RaritanPdu from a config entry."""
    config = await get_connection_details_from_entry(entry)

    try:
        client = RaritanClient(hass, config)
        pdu: RaritanPdu = await client.get_pdu_info()
    except AuthenticationError as ex:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="device_authentication",
            translation_placeholders={
                "func": "connect",
                "exc": str(ex),
            },
        ) from ex
    except CertificateVerificationError as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cert_error",
            translation_placeholders={
                "func": "connect",
                "exc": str(ex),
            },
        ) from ex
    except RaritanClientError as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="device_error",
            translation_placeholders={
                "func": "connect",
                "exc": str(ex),
            },
        ) from ex
    updates: dict[str, Any] = {}
    if entry.data.get(CONF_ALIAS) != pdu.name:
        updates[CONF_ALIAS] = pdu.name
    if entry.data.get(CONF_MODEL) != pdu.model:
        updates[CONF_MODEL] = pdu.model
    if updates:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                **updates,
            },
        )

    if pdu.serial_number != entry.unique_id:
        # If the serial number of the device does not match the unique_id
        # of the config entry, it likely means the DHCP lease has expired
        # and the device has been assigned a new IP address. We need to
        # wait for the next discovery to find the device at its new address
        # and update the config entry so we do not mix up devices.
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="unexpected_device",
            translation_placeholders={
                "host": config.host,
                # all entries have a unique id
                "expected": cast(str, entry.unique_id),
                "found": pdu.serial_number,
            },
        )

    coordinator = RaritanPduDataUpdateCoordinator(
        hass, _LOGGER, entry, UPDATE_INTERVAL, client, pdu
    )

    entry.runtime_data = RaritanPduData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    await entry.runtime_data.client.close_session()

    return unload_ok


async def get_credentials(hass: HomeAssistant, entry: RaritanPduConfigEntry | None = None) -> AuthenticationDetails:
    """Retrieve the credentials from hass data."""
    if entry and CONF_USERNAME in entry.data and CONF_PASSWORD in entry.data:
        return AuthenticationDetails(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    if DOMAIN in hass.data and CONF_AUTHENTICATION in hass.data[DOMAIN]:
        auth = hass.data[DOMAIN][CONF_AUTHENTICATION]
        return AuthenticationDetails(auth[CONF_USERNAME], auth[CONF_PASSWORD])

    return AuthenticationDetails(DEFAULT_USERNAME, DEFAULT_PASSWORD)

async def get_connection_details_from_entry(entry: RaritanPduConfigEntry) -> ConnectionDetails:
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    use_ssl: bool = entry.data[CONF_SSL]
    verify_ssl: bool = entry.data[CONF_VERIFY_SSL]
    credentials = AuthenticationDetails(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    return ConnectionDetails(
        host=host,
        auth=credentials,
        port=port,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
    )

async def set_credentials(
    hass: HomeAssistant, credentials: AuthenticationDetails | None
) -> None:
    """Save the credentials to HASS data."""

    if credentials:
        hass.data.setdefault(DOMAIN, {})[CONF_AUTHENTICATION] = {
            CONF_USERNAME: credentials.user,
            CONF_PASSWORD: credentials.passwd,
        }

async def async_migrate_entry(
    hass: HomeAssistant, config_entry: RaritanPduConfigEntry
) -> bool:
    """Migrate old entry."""
    entry_version: int = config_entry.version
    entry_minor_version: int = config_entry.minor_version

    if (entry_minor_version >= CONF_CONFIG_ENTRY_MINOR_VERSION):
        if (entry_minor_version > CONF_CONFIG_ENTRY_MINOR_VERSION):
            _LOGGER.warning("Config version is newer than expected")

        return True

    for new_minor_version in range(entry_minor_version + 1, CONF_CONFIG_ENTRY_MINOR_VERSION + 1):
        _LOGGER.debug(
            "Migrating from version %s.%s", entry_version, entry_minor_version
        )

        try:
            upgrade_fn = globals()[f"migrate_config_entry_to_version_{entry_version}_{new_minor_version}"]
            await upgrade_fn(hass, config_entry)

            hass.config_entries.async_update_entry(
                config_entry, minor_version=new_minor_version
            )

            _LOGGER.debug(
                "Migration to version %s.%s complete", entry_version, entry_minor_version := new_minor_version
            )
        except KeyError:
            _LOGGER.error(
                "Unable to migrate config to version %s.%s: Migration method not defined",
                entry_version,
                new_minor_version,
            )
        except Exception as e:
            _LOGGER.exception(
                "Unable to migrate config to version %s.%s: %s", entry_version, entry_minor_version, str(e)
            )

            return False

    return True

async def migrate_config_entry_to_version_1_2(
    hass: HomeAssistant, config_entry: RaritanPduConfigEntry
) -> None:
    updates = {
        **config_entry.data,
        **{
            CONF_PORT: DEFAULT_PORT,
            CONF_SSL: True,
            CONF_VERIFY_SSL: False,
        },
    }

    hass.config_entries.async_update_entry(
        config_entry, data=updates
    )
