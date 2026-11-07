"""Coordinator to gather data for Raritan PX2/PX3 PDUs."""

from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.raritan_px.const import DEFAULT_UPDATE_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from datetime import timedelta
    from logging import Logger

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.client import RaritanClient
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState


@dataclass(slots=True)
class RaritanPduData:
    """Data for the RaritanPdu integration."""

    client: RaritanClient
    coordinator: RaritanPduDataUpdateCoordinator
    hub: DeviceEntry


type RaritanPduConfigEntry = ConfigEntry[RaritanPduData]


class RaritanPduDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """DataUpdateCoordinator to gather data for a specific RaritanPdu device."""

    config_entry: RaritanPduConfigEntry
    client_lock: Lock

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        logger: Logger,
        config_entry: RaritanPduConfigEntry,
        client: RaritanClient,
        pdu: RaritanPdu,
        *,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the RaritanPdu coordinator."""
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name="RaritanPdu",
            update_interval=update_interval,
        )
        self.pdu = pdu
        self.client = client
        self.config_entry = config_entry
        self.client_lock = Lock()
        self._devices = self._cache_devices_by_id(pdu)

    def _cache_devices_by_id(self, pdu: RaritanPdu) -> dict[str, RaritanDevice]:
        devices: dict[str, RaritanDevice] = {}

        for _, device in [("", pdu), *pdu.inlets.items(), *pdu.outlets.items(), *pdu.ocps.items()]:
            devices[device.device_id] = device

        return devices

    async def _async_update_data(self) -> RaritanPdu:
        """Fetch all device and sensor data from api."""
        async with self.client_lock:
            try:
                device_ids = {device_id for device_id, _ in self.async_contexts()}

                if device_ids:
                    await self.client.update_sensor_readings_for_devices(
                        self.pdu, [self._devices[device_id] for device_id in device_ids]
                    )
                else:
                    await self.client.update_sensor_readings_for_pdu(self.pdu)
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
        async with self.client_lock:
            try:
                updated = await self.client.set_outlet_power_state(
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
