"""Raritan PX2/PX3 PDU Integration."""

import logging
import re
from asyncio import Lock
from typing import TYPE_CHECKING, Any, cast

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
    Platform,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.storage import Store

from custom_components.raritan_px.api.client import (
    AuthenticationError,
    CertificateVerificationError,
    RaritanClient,
)
from custom_components.raritan_px.api.client.errors import (
    FirmwareUpgradeInProgressError,
    RaritanClientError,
    RequestTimeoutError,
)
from custom_components.raritan_px.api.client.struct import AuthenticationDetails, ConnectionDetails
from custom_components.raritan_px.api.const import (
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
)
from custom_components.raritan_px.const import (
    CONF_CONFIG_ENTRY_MINOR_VERSION,
    DEFAULT_API_UPDATE_INTERVAL,
    DEFAULT_FIRMWARE_UPDATE_INTERVAL,
    DELAY_FIRST_FIRMWARE_CATALOGUE_UPDATE,
    DOMAIN,
    PLATFORMS,
)
from custom_components.raritan_px.coordinator import (
    RaritanApiDataUpdateCoordinator,
    RaritanFirmwareDataUpdateCoordinator,
    RaritanPduConfigEntry,
    RaritanPduData,
)
from custom_components.raritan_px.firmware import FirmwareManager
from custom_components.raritan_px.firmware.const import (
    CATALOGUE_MANAGER,
    CATALOGUE_STORE,
    CATALOGUE_STORE_STORAGE_KEY,
    CATALOGUE_STORE_STORAGE_VERSION,
)
from custom_components.raritan_px.services import async_setup_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.user import RaritanUser

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Set up the Raritan PX component."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[CATALOGUE_STORE] = Store(hass, CATALOGUE_STORE_STORAGE_VERSION, CATALOGUE_STORE_STORAGE_KEY)
    hass.data[CATALOGUE_MANAGER] = FirmwareManager(hass, delay_first_check=DELAY_FIRST_FIRMWARE_CATALOGUE_UPDATE)

    async_setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Set up RaritanPdu from a config entry."""
    config = await get_connection_details_from_entry(entry)
    lock = Lock()

    try:
        client = RaritanClient(hass, config)

        await client.ping(raise_exception=True)
    except RequestTimeoutError as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="api_unreachable",
            translation_placeholders={
                "host": config.host,
                "entry": entry.title,
            },
        ) from ex
    except RaritanClientError as ex:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="device_error",
            translation_placeholders={
                "func": "connect",
                "exc": str(ex),
            },
        ) from ex

    try:
        user: RaritanUser = await client.get_user()
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
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="cert_error",
            translation_placeholders={
                "func": "connect",
                "exc": str(ex),
            },
        ) from ex
    except FirmwareUpgradeInProgressError as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="firmware_update_in_progress",
            translation_placeholders={
                "state": ex.state,
                "elapsed": str(ex.elapsed),
                "remaining": str(ex.estimated - ex.elapsed),
            },
        ) from ex
    except RequestTimeoutError as ex:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="api_timeout",
            translation_placeholders={
                "host": config.host,
                "pdu": entry.title,
            },
        ) from ex
    except RaritanClientError as ex:
        raise ConfigEntryError(
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
                "expected": cast("str", entry.unique_id),
                "found": pdu.serial_number,
            },
        )

    device_registry = dr.async_get(hass)

    hub = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, str(pdu.device_id))},
        manufacturer=pdu.manufacturer,
        model=pdu.model,
        serial_number=pdu.serial_number,
        name=pdu.name or f"{pdu.model} {pdu.serial_number}",
        configuration_url=pdu.url,
        sw_version=pdu.firmware_version,
        hw_version=pdu.hardware_version,
        connections={
            (dr.CONNECTION_NETWORK_MAC, dr.format_mac(interface.mac_address))
            for _, interface in pdu.network_interfaces.items()
            if interface.mac_address
        },
    )

    _LOGGER.debug("Registered device %s", pdu.device_id)

    api_coordinator = RaritanApiDataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        client=client,
        client_lock=lock,
        pdu=pdu,
        user=user,
        update_interval=DEFAULT_API_UPDATE_INTERVAL,
    )
    firmware_coordinator = RaritanFirmwareDataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        client=client,
        client_lock=lock,
        manager=hass.data[CATALOGUE_MANAGER],
        pdu=pdu,
        user=user,
        update_interval=DEFAULT_FIRMWARE_UPDATE_INTERVAL,
    )

    await api_coordinator.async_config_entry_first_refresh()
    await firmware_coordinator.async_refresh()

    entry.runtime_data = RaritanPduData(
        client=client,
        client_lock=lock,
        user=user,
        api_coordinator=api_coordinator,
        firmware_coordinator=firmware_coordinator,
        hub=hub,
        pdu=pdu,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RaritanPduConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    async with entry.runtime_data.client_lock:
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


async def get_connection_details_from_entry(
    entry: RaritanPduConfigEntry,
) -> ConnectionDetails:
    """Get PDU connection details struct from config entry."""
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


async def set_credentials(hass: HomeAssistant, credentials: AuthenticationDetails | None) -> None:
    """Save the credentials to HASS data."""
    if credentials:
        hass.data.setdefault(DOMAIN, {})[CONF_AUTHENTICATION] = {
            CONF_USERNAME: credentials.user,
            CONF_PASSWORD: credentials.passwd,
        }


async def async_migrate_entry(hass: HomeAssistant, config_entry: RaritanPduConfigEntry) -> bool:
    """Migrate old entry."""
    entry_version: int = config_entry.version
    entry_minor_version: int = config_entry.minor_version

    if entry_minor_version >= CONF_CONFIG_ENTRY_MINOR_VERSION:
        if entry_minor_version > CONF_CONFIG_ENTRY_MINOR_VERSION:
            _LOGGER.warning("Config version is newer than expected")

        return True

    for new_minor_version in range(entry_minor_version + 1, CONF_CONFIG_ENTRY_MINOR_VERSION + 1):
        _LOGGER.debug("Migrating from version %s.%s", entry_version, entry_minor_version)

        try:
            upgrade_fn = globals()[f"migrate_config_entry_to_version_{entry_version}_{new_minor_version}"]
            await upgrade_fn(hass, config_entry)

            hass.config_entries.async_update_entry(config_entry, minor_version=new_minor_version)

            _LOGGER.debug(
                "Migration to version %s.%s complete",
                entry_version,
                entry_minor_version := new_minor_version,
            )
        except KeyError:
            _LOGGER.exception(
                "Unable to migrate config to version %s.%s: Migration method not defined",
                entry_version,
                new_minor_version,
            )
        except Exception:
            _LOGGER.exception("Unable to migrate config to version %s.%s", entry_version, entry_minor_version)

            return False

    return True


async def migrate_config_entry_to_version_1_2(hass: HomeAssistant, config_entry: RaritanPduConfigEntry) -> None:
    """Migrate config entry data to 1.2."""
    updates = {
        **config_entry.data,
        CONF_PORT: DEFAULT_PORT,
        CONF_SSL: True,
        CONF_VERIFY_SSL: False,
    }

    hass.config_entries.async_update_entry(config_entry, data=updates)


def _get_new_entity_unique_id(entity: er.RegistryEntry) -> str:
    new_unique_id = entity.unique_id

    if entity.domain == Platform.SWITCH:
        new_unique_id = re.sub(
            r"^(?P<device_id>[^:]+:[^_:]+)_(?P<entity_key>.+)$",
            r"\g<device_id>::switch::\g<entity_key>",
            new_unique_id,
        )
    else:
        # Migrate attribute backed entities
        new_unique_id = re.sub(
            r"^(?P<device_id>[^:]+:[^_:]+)_prop_(?P<entity_key>.+)$",
            r"\g<device_id>::attribute::\g<entity_key>",
            new_unique_id,
        )

        # Replace colon in multi-statesensor entities
        new_unique_id = re.sub(
            r"^(?P<device_id>[^:]+:[^_:]+)_(?P<entity_key>.+):(?P<index>[0-9]+)$",
            r"\g<device_id>::sensor::\g<entity_key>_\g<index>",
            new_unique_id,
        )

        # Migrate remaining sensor backed entities
        new_unique_id = re.sub(
            r"^(?P<device_id>[^:]+:[^_:]+)_(?P<entity_key>.+)$",
            r"\g<device_id>::sensor::\g<entity_key>",
            new_unique_id,
        )

    return new_unique_id


async def migrate_config_entry_to_version_1_3(hass: HomeAssistant, config_entry: RaritanPduConfigEntry) -> None:
    """Migrate config entry data to 1.3."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    migrated = 0

    for entity in entities:
        new_unique_id = _get_new_entity_unique_id(entity)

        if new_unique_id != entity.unique_id:
            try:
                entity_registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

                migrated += 1
            except ValueError:
                pass

    _LOGGER.info("Migrated unique IDs of %s of %s entities", migrated, len(entities))


async def migrate_config_entry_to_version_1_4(hass: HomeAssistant, config_entry: RaritanPduConfigEntry) -> None:
    """Migrate config entry data to 1.4."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    removed = 0

    # Handle upgrade after downgrading from 2.10 to 2.0.1
    entity_unique_ids = {(entity.domain, entity.unique_id): entity.entity_id for entity in entities}

    for entity in entities:
        if entity.previous_unique_id and (entity.domain, entity.previous_unique_id) in entity_unique_ids:
            # Remove the entity so the old enand remigrate the old entity
            entity_registry.async_remove(entity_unique_ids[(entity.domain, entity.previous_unique_id)])

            removed += 1

    _LOGGER.info("Removed %s dangling entities after downgrade", removed)

    entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    migrated = 0

    for entity in entities:
        if entity.previous_unique_id:
            continue

        new_unique_id = _get_new_entity_unique_id(entity)

        if new_unique_id != entity.unique_id:
            try:
                entity_registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

                migrated += 1
            except ValueError:
                pass

    _LOGGER.info("Re-migrated unique IDs of %s of %s entities", migrated, len(entities))
