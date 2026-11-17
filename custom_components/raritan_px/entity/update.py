"""Raritan PDU update entities."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback

from custom_components.raritan_px.coordinator import RaritanFirmwareDataUpdateCoordinator
from custom_components.raritan_px.entity import (
    CoordinatedRaritanDeviceEntity,
    CoordinatedRaritanPduEntity,
)
from custom_components.raritan_px.entity.descriptions import (
    RaritanDeviceEntityDescription,
    RaritanPduEntityDescription,
)
from custom_components.raritan_px.firmware.model import Firmware

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.coordinator import RaritanFirmwareDataUpdateCoordinator


class RaritanDeviceUpdateEntity(CoordinatedRaritanDeviceEntity, UpdateEntity):
    """Base class of a Raritan device update."""

    entity_description: RaritanDeviceUpdateEntityDescription
    coordinator: RaritanFirmwareDataUpdateCoordinator

    def __init__(
        self,
        coordinator: RaritanFirmwareDataUpdateCoordinator,
        *,
        description: RaritanDeviceEntityDescription,
        device: RaritanDevice,
        hub: DeviceEntry,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, device=device, hub=hub, description=description)

    @classmethod
    def _entity_type(cls) -> str:
        return "update"

    @classmethod
    def _entity_source(cls) -> str:
        return "catalogue"


class RaritanPduUpdateEntity(CoordinatedRaritanPduEntity, RaritanDeviceUpdateEntity):
    """Representation of a Raritan PDU update entity."""

    entity_description: RaritanPduUpdateEntityDescription


class RaritanPduFirmwareUpdateEntity(RaritanPduUpdateEntity):
    """Representation of a Raritan PDU update entity."""

    entity_description: RaritanPduUpdateEntityDescription
    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(
        self,
        coordinator: RaritanFirmwareDataUpdateCoordinator,
        *,
        description: RaritanPduUpdateEntityDescription,
        device: RaritanPdu,
        hub: DeviceEntry,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, device=device, hub=hub, description=description)

        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        self._attr_installed_version = str(Firmware.normalise(self._device.firmware_version))

        if self.coordinator.latest_firmware:
            self._attr_latest_version = self.coordinator.latest_firmware.version

            if self.coordinator.latest_firmware.release_notes_url:
                self._attr_release_url = str(self.coordinator.latest_firmware.release_notes_url)

        return True


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceUpdateEntityDescription(UpdateEntityDescription, RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU device sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduUpdateEntityDescription(RaritanDeviceUpdateEntityDescription, RaritanPduEntityDescription):
    """Base class for a Raritan PDU sensor entity description."""


PDU_FIRMWARE_UPDATE_DESCRIPTION: RaritanPduUpdateEntityDescription = RaritanPduUpdateEntityDescription(
    key="firmware_version",
    device_class=UpdateDeviceClass.FIRMWARE,
    entity_category=EntityCategory.DIAGNOSTIC,
)
