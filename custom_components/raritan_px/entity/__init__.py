"""Common code for RaritanPdu."""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from homeassistant.core import callback

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.raritan_px.entity.description import (
    RaritanPduDeviceEntityDescription,
    RaritanPduEntityDescription,
    RaritanPduOutletEntityDescription,
    RaritanPduOverCurrentProtectorEntityDescription,
    RaritanPduInletEntityDescription,
)
from custom_components.raritan_px.api.model.device import (
    RaritanPdu,
    RaritanPduDevice,
    RaritanPduEnergyDevice,
    RaritanPduInlet,
    RaritanPduOutlet,
    RaritanPduOverCurrentProtector,
)
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator
from custom_components.raritan_px.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class CoordinatedRaritanPduDeviceEntity(
    CoordinatorEntity[RaritanPduDataUpdateCoordinator], ABC
):
    """Common base class for all coordinated raritan pdu entities."""

    _attr_has_entity_name = True
    _device: RaritanPduDevice
    _pdu: RaritanPdu

    entity_description: RaritanPduDeviceEntityDescription

    def __init__(
        self,
        device: RaritanPduDevice,
        pdu: RaritanPdu,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanPduDeviceEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._pdu = pdu

        self._attr_device_info = self._get_device_info()
        self._attr_unique_id = f"{device.device_id}_{description.key}"

    def _get_pdu_name(self) -> str:
        """Get the pdu name to use for this entity."""
        if self._pdu.name:
            return self._pdu.name

        return f"{self._pdu.model} {self._pdu.serial_number}"

    @staticmethod
    def _merge_device_info(info: DeviceInfo, merge: DeviceInfo) -> DeviceInfo:
        return DeviceInfo(**{**info, **merge}) # pyright: ignore[reportArgumentType]

    def _get_device_info(self) -> DeviceInfo:
        return self._merge_device_info(
            DeviceInfo(
                identifiers={(DOMAIN, str(self._device.device_id))},
                manufacturer=self._pdu.manufacturer,
                model=self._get_device_model(),
                name=self._get_device_name(),
                configuration_url=self._device.url,
            ),
            self._get_device_connection_info()
        )

    def _get_device_connection_info(self) -> DeviceInfo:
        return DeviceInfo(
            via_device=(DOMAIN, self._pdu.device_id)
        )

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> bool:
        """Platforms implement this to update the entity internals.

        The return value is used to the set the entity available attribute.
        """
        raise NotImplementedError

    @callback
    def _async_call_update_attrs(self) -> None:
        """Call update_attrs and make entity unavailable on errors."""
        try:
            available = self._async_update_attrs()
        except Exception as ex:  # noqa: BLE001
            if self._attr_available:
                _LOGGER.warning(
                    "Unable to read data for %s %s: %s",
                    self._device,
                    self.entity_id,
                    ex,
                )
            self._attr_available = False
        else:
            self._attr_available = available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._async_call_update_attrs()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._attr_available

    @abstractmethod
    def _get_device_name(self) -> str | None:
        """Get the device name to use for this entity."""
        raise NotImplementedError

    @abstractmethod
    def _get_device_model(self) -> str | None:
        """Get the device model to use for this entity."""
        raise NotImplementedError

class CoordinatedRaritanPduEntity(CoordinatedRaritanPduDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPdu
    entity_description: RaritanPduEntityDescription

    def _get_device_name(self) -> str:
        """Get the device name to use for this entity."""
        return self._get_pdu_name()

    def _get_device_model(self) -> str:
        """Get the device model to use for this entity."""
        return self._pdu.model

    def _get_device_info(self) -> DeviceInfo:
        return self._merge_device_info(
            super()._get_device_info(),
            DeviceInfo(
                sw_version=self._pdu.firmware_version,
                hw_version=self._pdu.hardware_version,
            )
        )

    def _get_device_connection_info(self) -> DeviceInfo:
        return DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, self._pdu.mac_address)},
        )

class CoordinatedRaritanPduEnergyDeviceEntity(CoordinatedRaritanPduDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPduEnergyDevice
    entity_description: RaritanPduDeviceEntityDescription

    def _get_device_name(self) -> str | None:
        """Get the device name to use for this entity."""
        if self._device.name:
            return self._device.name

        return f"{self._get_pdu_name()} {self._get_device_type()} {self._device.label}"

    def _get_device_model(self) -> str:
        """Get the device model to use for this entity."""
        return f"{self._pdu.model} {self._get_device_type()}"

    @abstractmethod
    def _get_device_type(self) -> str:
        """Get the device type to use for this entity."""
        raise NotImplementedError


class CoordinatedRaritanPduOutletEntity(CoordinatedRaritanPduEnergyDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletEntityDescription

    def _get_device_type(self) -> str:
        """Get the device type to use for this entity."""
        return "Outlet"


class CoordinatedRaritanPduInletEntity(CoordinatedRaritanPduEnergyDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletEntityDescription

    def _get_device_type(self) -> str:
        """Get the device type to use for this entity."""
        return "Inlet"


class CoordinatedRaritanPduOverCurrentProtectorEntity(CoordinatedRaritanPduEnergyDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPduOverCurrentProtector
    entity_description: RaritanPduOverCurrentProtectorEntityDescription

    def _get_device_type(self) -> str:
        """Get the device type to use for this entity."""
        return "Overcurrent Protector"
