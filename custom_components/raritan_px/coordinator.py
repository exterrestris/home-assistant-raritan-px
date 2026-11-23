"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
from typing import TYPE_CHECKING, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.raritan_px.api.client import RaritanClient, RaritanClientError
from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
from custom_components.raritan_px.api.model.user import Privilege, RaritanUser
from custom_components.raritan_px.const import (
    DOMAIN,
    FIRMWARE_DOWNLOAD_PROGRESS_WEIGHT,
    FIRMWARE_UPDATE_PROGRESS_WEIGHT,
    FIRMWARE_UPLOAD_PROGRESS_WEIGHT,
    IN_PROGRESS_FIRMWARE_UPDATE_INTERVAL,
    POST_FIRMWARE_DOWNLOAD_DELAY,
    POST_FIRMWARE_UPDATE_DELAY,
    POST_FIRMWARE_UPLOAD_DELAY,
)
from custom_components.raritan_px.firmware import FirmwareManagerError
from custom_components.raritan_px.utils.decorators import SetProperty, Sleep

if TYPE_CHECKING:
    from asyncio import Lock
    from datetime import timedelta
    from logging import Logger
    from pathlib import Path

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.client import RaritanClient
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState
    from custom_components.raritan_px.firmware import FirmwareManager
    from custom_components.raritan_px.firmware.model import Firmware, FirmwareCatalogue


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    client: RaritanClient
    user: RaritanUser
    client_lock: Lock
    api_coordinator: RaritanApiDataUpdateCoordinator
    firmware_coordinator: RaritanFirmwareDataUpdateCoordinator
    pdu: RaritanPdu
    hub: DeviceEntry


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]


class RaritanDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Base DataUpdateCoordinator."""

    _client: RaritanClient
    _client_lock: Lock
    _default_interval: timedelta
    config_entry: RaritanPduConfigEntry
    pdu: RaritanPdu
    user: RaritanUser
    firmware_update_in_progress: bool = False

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
        user: RaritanUser,
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
        self.user = user
        self._client = client
        self._client_lock = client_lock
        self._default_interval = update_interval

    def _set_update_interval(self, update_interval: timedelta) -> None:
        self.update_interval = update_interval
        self._schedule_refresh()

    def _reset_update_interval(self) -> None:
        self._set_update_interval(self._default_interval)


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
        user: RaritanUser,
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
            user=user,
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
        # This call can be made safely without acquiring the client lock
        self.firmware_update_in_progress = await self._client.is_firmware_update_in_progress()

        if self.firmware_update_in_progress:
            return self.pdu

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
                updated = await self._client.set_outlet_power_state(outlet, state)
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

    _manager: FirmwareManager
    catalogue: FirmwareCatalogue | None = None
    latest_firmware: Firmware | None = None
    catalogue_update_check: bool = False  # Don't check for a catalogue update on first refresh
    _firmware_update_started: bool = False
    _firmware_download_progress: float | None
    _firmware_upload_progress: float | None
    _firmware_update_progress: float | None
    firmware_update_percentage: float | None

    @override
    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        config_entry: RaritanPduConfigEntry,
        client: RaritanClient,
        client_lock: Lock,
        manager: FirmwareManager,
        pdu: RaritanPdu,
        user: RaritanUser,
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
            user=user,
            name="firmware management",
            update_interval=update_interval,
        )
        self._manager = manager
        self._bulk_set_progress()

    def _bulk_set_progress(self, value: float | None = None) -> None:
        self.firmware_update_percentage = value
        self._firmware_download_progress = value
        self._firmware_upload_progress = value
        self._firmware_update_progress = value

    async def _async_update_data(self) -> None:
        """Fetch firmware data."""
        self.firmware_update_in_progress = self.firmware_update_percentage is not None
        self._firmware_update_started = await self._client.is_firmware_update_in_progress()

        if self.firmware_update_in_progress:
            try:
                if self._firmware_update_started:
                    status = await self._client.get_firmware_update_status()

                    self._firmware_update_progress = (
                        min(100, status.elapsed / status.estimated * 100) if status.estimated else None
                    )
                else:
                    status = await self._client.get_firmware_upload_status()

                    self._firmware_upload_progress = (
                        float(status) if status is not None and not isinstance(status, str) else 0
                    )

                self.firmware_update_percentage = (
                    (self._firmware_download_progress or 0) * FIRMWARE_DOWNLOAD_PROGRESS_WEIGHT
                    + (self._firmware_upload_progress or 0) * FIRMWARE_UPLOAD_PROGRESS_WEIGHT
                    + (self._firmware_update_progress or 0) * FIRMWARE_UPDATE_PROGRESS_WEIGHT
                )
            except Exception as ex:
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="firmware_update_status_failed",
                    translation_placeholders={
                        "exc": str(ex),
                    },
                ) from ex
        else:
            self._bulk_set_progress()

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

    def _update_download_progess(self, downloaded: int, total: int) -> None:
        self._firmware_download_progress = min(100, downloaded / total * 100)

    async def update_firmware(self, version: str | None = None) -> None:
        """Update firmware of the PDU defined by the config entry for this coordinator."""
        if not self.config_entry.runtime_data.user.can(Privilege.FIRMWARE_UPDATE):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="firmware_update_forbidden",
                translation_placeholders={
                    "pdu": self.pdu.device_name,
                },
            )

        try:
            firmware = await self._identify_firmware(version)

            self._bulk_set_progress(0)
            self._set_update_interval(IN_PROGRESS_FIRMWARE_UPDATE_INTERVAL)

            fw_bin = await self._download_firmware(firmware)
            await self._upload_firmware(fw_bin)
            await self._update_firmware()
            await self._refresh_pdu_firmware_version()
        except (FirmwareManagerError, RaritanClientError) as err:
            if (self._firmware_upload_progress or 0) > 0:
                try:
                    await self._client.cancel_firmware_update()
                except RaritanClientError:
                    self.logger.warning("Unable to cancel firmare update", exc_info=True)

            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="firmware_update_failed",
                translation_placeholders={"exc": str(err) or err.__class__.__name__},
            ) from err
        finally:
            self._bulk_set_progress()
            await self.async_request_refresh()
            self._reset_update_interval()

    async def _identify_firmware(self, fw_version: str | None) -> Firmware:
        if not self.catalogue:
            self.catalogue = await self._manager.get_catalogue()

        if fw_version:
            firmware = self.catalogue.get_firmware(fw_version, self.pdu.model, self.pdu.firmware_version)

            translation_key = "firmware_model_not_supported"
            translation_placeholders = {
                "model": self.pdu.model,
                "version": fw_version,
            }
        else:
            if not self.latest_firmware:
                self.latest_firmware = self.catalogue.get_latest_firmware(self.pdu.model, self.pdu.firmware_version)

            firmware = self.latest_firmware

            translation_key = "firmware_is_latest"
            translation_placeholders = {
                "model": self.pdu.model,
                "version": self.pdu.firmware_version,
            }

        if not firmware:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
            )

        return firmware

    @SetProperty("_firmware_download_progress", before=0, after=100)
    @Sleep(after=POST_FIRMWARE_DOWNLOAD_DELAY)
    async def _download_firmware(self, firmware: Firmware) -> Path:
        def _track_progess(downloaded: int, total: int) -> None:
            self._firmware_download_progress = min(100, downloaded / total * 100)

        (fw_bin, _fw_bin_size) = await self._manager.download_firmware(firmware, callback=_track_progess)

        return fw_bin

    @SetProperty("_firmware_upload_progress", before=0, after=100)
    @Sleep(after=POST_FIRMWARE_UPLOAD_DELAY)
    async def _upload_firmware(self, fw_bin: Path) -> None:
        await self._client.upload_firmware(fw_bin)

    @SetProperty("_firmware_update_progress", before=0, after=100)
    @Sleep(after=POST_FIRMWARE_UPDATE_DELAY)
    async def _update_firmware(self) -> None:
        await self._client.start_firmware_update()
        await self._client.wait_for_firmware_update()

    async def _refresh_pdu_firmware_version(self) -> None:
        await self._client.refresh_pdu_firmware_version(self.pdu)
        device_registry = dr.async_get(self.hass)
        device_registry.async_update_device(self.config_entry.runtime_data.hub.id, sw_version=self.pdu.firmware_version)
