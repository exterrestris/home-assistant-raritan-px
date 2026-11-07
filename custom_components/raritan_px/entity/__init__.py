"""Raritan PDU base entities."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.raritan_px.const import DOMAIN
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator

if TYPE_CHECKING:
    from custom_components.raritan_px.api.model.device import (
        RaritanDevice,
        RaritanEnergyDevice,
    )
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
        RaritanPduEntityDescription,
        RaritanPduInletEntityDescription,
        RaritanPduOutletEntityDescription,
        RaritanPduOverCurrentProtectorEntityDescription,
    )

_LOGGER = logging.getLogger(__name__)


class CoordinatedRaritanDeviceEntity(CoordinatorEntity[RaritanPduDataUpdateCoordinator], ABC):
    """Common base class for all coordinated raritan device entities."""

    _attr_has_entity_name = True
    _device: RaritanDevice
    _pdu: RaritanPdu
    _hub: DeviceEntry

    entity_description: RaritanDeviceEntityDescription

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, context=(device.device_id, description.key))

        self.entity_description = description
        self._device = device
        self._pdu = coordinator.pdu
        self._hub = hub

        self._attr_device_info = self._get_device_info()
        self._attr_unique_id = self._get_unique_id()

        _LOGGER.debug("Created %s %s for %s", description.key, self._entity_type(), device.device_id)

    def _get_unique_id(self) -> str:
        return f"{self._device.device_id}_{self.entity_description.key}"

    @abstractmethod
    def _entity_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _get_device_info(self) -> DeviceInfo:
        raise NotImplementedError

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> bool:
        """
        Platforms implement this to update the entity internals.

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


class CoordinatedRaritanPduEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu based entities."""

    _device: RaritanPdu
    entity_description: RaritanPduEntityDescription

    def _get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.device_id))},
            manufacturer=self._device.manufacturer,
            model=self._device.device_model,
            name=self._device.device_name,
            configuration_url=self._device.url,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._device.mac_address)},
        )


class CoordinatedRaritanEnergyDeviceEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan energy device based entities."""

    _device: RaritanEnergyDevice
    entity_description: RaritanDeviceEntityDescription

    def _get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.device_id))},
            manufacturer=self._device.pdu.manufacturer,
            model=self._device.device_model,
            name=self._device.device_name,
            via_device_id=self._hub.id,
        )


class CoordinatedRaritanPduOutletEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu outlet based entities."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletEntityDescription


class CoordinatedRaritanPduInletEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu inlet based entities."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletEntityDescription


class CoordinatedRaritanPduOverCurrentProtectorEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu overcurrent protector based entities."""

    _device: RaritanPduOverCurrentProtector
    entity_description: RaritanPduOverCurrentProtectorEntityDescription
