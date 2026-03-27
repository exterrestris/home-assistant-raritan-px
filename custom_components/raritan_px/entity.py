"""Common code for RaritanPdu."""

from __future__ import annotations
from dataclasses import dataclass
import logging

from abc import ABC, abstractmethod
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .api import (
    RaritanPduDevice,
    RaritanPdu,
    RaritanPduEnergyDevice,
    RaritanPduOutlet,
)
from .coordinator import RaritanPduDataUpdateCoordinator

from .const import (
    DOMAIN,
)
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RaritanPduEntityDescription(EntityDescription):
    """Base class for a Raritan PDU entity description."""


class CoordinatedRaritanPduDeviceEntity(
    CoordinatorEntity[RaritanPduDataUpdateCoordinator], ABC
):
    """Common base class for all coordinated raritan pdu entities."""

    _attr_has_entity_name = True
    _device: RaritanPduDevice

    entity_description: RaritanPduEntityDescription

    def __init__(
        self,
        device: RaritanPduDevice,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanPduEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device

        registry_device = device
        device_name = self._get_device_name()

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(registry_device.device_id))},
            manufacturer="Raritan",
            name=device_name,
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


class CoordinatedRaritanPduEntity(CoordinatedRaritanPduDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPdu

    def __init__(
        self,
        device: RaritanPdu,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanPduEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(device, coordinator, description)

    def _get_device_name(self) -> str | None:
        """Get the device name to use for this entity."""
        if self._device.name:
            return self._device.name

        return f"{self._device.model} {self._device.serial_number}"


class CoordinatedRaritanPduEnergyDeviceEntity(CoordinatedRaritanPduDeviceEntity, ABC):
    """Common base class for all coordinated tplink module based entities."""

    _device: RaritanPduEnergyDevice

    def __init__(
        self,
        device: RaritanPduEnergyDevice,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanPduEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(device, coordinator, description)

    def _get_device_name(self) -> str | None:
        """Get the device name to use for this entity."""
        if self._device.name:
            return self._device.name

        return f"Outlet {self._device.label}"
