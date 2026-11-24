"""Raritan PDU update entities."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
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


class RaritanPduFirmwareUpdateEntity(RaritanPduUpdateEntity):
    """Representation of a Raritan PDU update entity."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_release_summary = "Device entities will be unavailable while firmware update is in progress"
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS | UpdateEntityFeature.SPECIFIC_VERSION
    )

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        self._attr_installed_version = str(Firmware.normalise(self._device.firmware_version))

        if self.coordinator.latest_firmware:
            self._attr_latest_version = self.coordinator.latest_firmware.version

            if self.coordinator.latest_firmware.release_notes_url:
                self._attr_release_url = str(self.coordinator.latest_firmware.release_notes_url)

        self._attr_in_progress = self.coordinator.firmware_update_in_progress
        self._attr_update_percentage = self.coordinator.firmware_update_percentage

        return True

    @property
    @override
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self._attr_latest_version if self.coordinator.latest_firmware else self._attr_installed_version

    @override
    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update."""
        await self.coordinator.update_firmware(version)


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
