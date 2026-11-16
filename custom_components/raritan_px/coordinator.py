"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
from typing import TYPE_CHECKING

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
    from custom_components.raritan_px.firmware.model import Firmware


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    client: RaritanClient
    client_lock: Lock
    api_coordinator: RaritanApiDataUpdateCoordinator
    firmware_coordinator: RaritanFirmwareDataUpdateCoordinator
    hub: DeviceEntry


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]


class RaritanDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Base DataUpdateCoordinator."""

    pdu: RaritanPdu
    _client: RaritanClient
    _client_lock: Lock

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
    """DataUpdateCoordinator to gather data for a specific RaritanPdu device."""

    _devices: dict[str, RaritanDevice]

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
        """Initialize the RaritanPdu coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            client=client,
            client_lock=client_lock,
            pdu=pdu,
            name="RaritanPduApi",
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
        async with self._client_lock:
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
                    translation_key="device_error",
                    translation_placeholders={
                        "func": "update_outlets",
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
                    translation_key="device_error",
                    translation_placeholders={
                        "func": "set_outlet_state",
                        "exc": str(ex),
                    },
                ) from ex
            else:
                return updated == state


class RaritanFirmwareDataUpdateCoordinator(RaritanDataUpdateCoordinator):
    """DataUpdateCoordinator to gather data for a specific RaritanPdu device."""

    _manager: FirmwareCatalogueManager
    latest_firmware: Firmware | None = None

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
        """Initialize the RaritanPdu coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            client=client,
            client_lock=client_lock,
            pdu=pdu,
            name="RaritanPduFirmware",
            update_interval=update_interval,
        )
        self._manager = manager

    async def _async_update_data(self) -> None:
        """Fetch firmware data."""
        try:
            catalogue = await self._manager.get_catalogue()

            self.latest_firmware = catalogue.get_latest_firmware(self.pdu.model, self.pdu.firmware_version)
        except Exception as ex:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="device_error",
                translation_placeholders={
                    "func": "update_outlets",
                    "exc": str(ex),
                },
            ) from ex
