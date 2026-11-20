"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
from typing import TYPE_CHECKING, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.raritan_px.api.client import RaritanClient
from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
from custom_components.raritan_px.const import DOMAIN

if TYPE_CHECKING:
    from asyncio import Lock
    from datetime import timedelta
    from logging import Logger

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.client import RaritanClient
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState
    from custom_components.raritan_px.firmware import FirmwareCatalogueManager
    from custom_components.raritan_px.firmware.model import Firmware, FirmwareCatalogue


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    client: RaritanClient
    client_lock: Lock
    api_coordinator: RaritanApiDataUpdateCoordinator
    firmware_coordinator: RaritanFirmwareDataUpdateCoordinator
    pdu: RaritanPdu
    hub: DeviceEntry


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]


class RaritanDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Base DataUpdateCoordinator."""

    pdu: RaritanPdu
    _client: RaritanClient
    _client_lock: Lock

    @override
    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        name: str,
        config_entry: RaritanPduConfigEntry,
        client: RaritanClient,
        client_lock: Lock,
        pdu: RaritanPdu,
        update_interval: timedelta,
    ) -> None:
        """Initialize the RaritanPdu coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name=name,
            update_interval=update_interval,
        )
        self.pdu = pdu
        self._client = client
        self._client_lock = client_lock


class RaritanApiDataUpdateCoordinator(RaritanDataUpdateCoordinator):
    """DataUpdateCoordinator to gather data from the JSON-RPC API for a specific Raritan PDU."""

    _devices: dict[str, RaritanDevice]

    @override
    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        config_entry: RaritanPduConfigEntry,
        client: RaritanClient,
        client_lock: Lock,
        pdu: RaritanPdu,
        update_interval: timedelta,
    ) -> None:
        """Initialize the JSON-RPC API coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            client=client,
            client_lock=client_lock,
            pdu=pdu,
            name=f"{pdu.device_name} API",
            update_interval=update_interval,
        )
        self._devices = self._cache_devices_by_id(pdu)

    def _cache_devices_by_id(self, pdu: RaritanPdu) -> dict[str, RaritanDevice]:
        devices: dict[str, RaritanDevice] = {}

        for _, device in [("", pdu), *pdu.inlets.items(), *pdu.outlets.items(), *pdu.ocps.items()]:
            devices[device.device_id] = device

        return devices

    async def _async_update_data(self) -> RaritanPdu:
        """Fetch all device and sensor data from api."""
        try:
            device_ids = {device_id for device_id, _ in self.async_contexts()}

            if device_ids:
                await self._client.update_sensor_readings_for_devices(
                    self.pdu, [self._devices[device_id] for device_id in device_ids]
                )
            else:
                await self._client.update_sensor_readings_for_pdu(self.pdu)
        except Exception as ex:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="api_update_error",
                translation_placeholders={
                    "pdu": self.pdu.device_name,
                    "exc": str(ex),
                },
            ) from ex
        else:
            return self.pdu

    async def set_outlet_power_state(self, outlet: RaritanPduOutlet, state: OutletPowerState) -> bool:
        """Set the state of an outlet."""
        async with self._client_lock:
            try:
                updated = await self._client.set_outlet_power_state(
                    outlet.pdu.id,
                    outlet.id,
                    state,
                )
            except Exception as ex:
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="api_change_outlet_state_error",
                    translation_placeholders={
                        "outlet": outlet.device_name,
                        "exc": str(ex),
                    },
                ) from ex
            else:
                return updated == state


class RaritanFirmwareDataUpdateCoordinator(RaritanDataUpdateCoordinator):
    """DataUpdateCoordinator to gather firmware update data for a specific Raritan PDU."""

    _manager: FirmwareCatalogueManager
    catalogue: FirmwareCatalogue | None = None
    latest_firmware: Firmware | None = None
    catalogue_update_check: bool = False  # Don't check for a catalogue update on first refresh

    @override
    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        config_entry: RaritanPduConfigEntry,
        client: RaritanClient,
        client_lock: Lock,
        manager: FirmwareCatalogueManager,
        pdu: RaritanPdu,
        update_interval: timedelta,
    ) -> None:
        """Initialize the firmware update coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            client=client,
            client_lock=client_lock,
            pdu=pdu,
            name="firmware catalogue",
            update_interval=update_interval,
        )
        self._manager = manager

    async def _async_update_data(self) -> None:
        """Fetch firmware data."""
        try:
            self.catalogue = await self._manager.get_catalogue(update_check=self.catalogue_update_check)

            self.latest_firmware = self.catalogue.get_latest_firmware(self.pdu.model, self.pdu.firmware_version)

            # Ensure subsequent data updates check for a catalogue update
            self.catalogue_update_check = True
        except Exception as ex:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="catalogue_error",
                translation_placeholders={
                    "exc": str(ex),
                },
            ) from ex
