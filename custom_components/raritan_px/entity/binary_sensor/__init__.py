"""Raritan PDU sensor entities."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback

from custom_components.raritan_px.entity import (
    CoordinatedRaritanDeviceAttributeBackedEntity,
    CoordinatedRaritanDeviceEntity,
    CoordinatedRaritanDeviceSensorBackedEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduInletEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduOverCurrentProtectorEntity,
    EntityValue,
)

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator
    from custom_components.raritan_px.entity.binary_sensor.descriptions import (
        RaritanDeviceBinarySensorEntityDescription,
        RaritanPduBinarySensorEntityDescription,
        RaritanPduInletBinarySensorEntityDescription,
        RaritanPduOutletBinarySensorEntityDescription,
        RaritanPduOverCurrentProtectorBinarySensorEntityDescription,
    )
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
    )


class RaritanDeviceBinarySensorEntity(CoordinatedRaritanDeviceEntity, BinarySensorEntity):
    """Base class of a Raritan PDU device sensor."""

    entity_description: RaritanDeviceBinarySensorEntityDescription

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
    ) -> None:
        """Initialise the entity."""
        super().__init__(device, hub, coordinator, description)

    def _get_value(self) -> EntityValue:
        raise NotImplementedError

    def _entity_type(self) -> str:
        return "binary sensor"

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._get_value()

        if value is not None:
            value = value == self.entity_description.on_value

        self._attr_is_on = value

        return True


class RaritanDeviceAttributeBackedBinarySensorEntity(
    CoordinatedRaritanDeviceAttributeBackedEntity, RaritanDeviceBinarySensorEntity
):
    """Representation of a Raritan PDU device property backed sensor."""

    def _get_value(self) -> EntityValue:
        return self._get_raw_device_attr_value()


class RaritanPduAttributeBackedBinarySensorEntity(
    CoordinatedRaritanPduEntity, RaritanDeviceAttributeBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet attribute backed sensor."""

    entity_description: RaritanPduBinarySensorEntityDescription


class RaritanPduOutletAttributeBackedBinarySensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceAttributeBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet attribute backed sensor."""

    entity_description: RaritanPduOutletBinarySensorEntityDescription


class RaritanPduInletAttributeBackedBinarySensorEntity(
    CoordinatedRaritanPduInletEntity, RaritanDeviceAttributeBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Inlet attribute backed sensor."""

    entity_description: RaritanPduInletBinarySensorEntityDescription


class RaritanPduOverCurrentProtectorAttributeBackedBinarySensorEntity(
    CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanDeviceAttributeBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Inlet attribute backed sensor."""

    entity_description: RaritanPduOverCurrentProtectorBinarySensorEntityDescription


class RaritanDeviceBinarySensorBackedBinarySensorEntity(
    CoordinatedRaritanDeviceSensorBackedEntity, RaritanDeviceBinarySensorEntity
):
    """Representation of a Raritan device sensor backed sensor."""

    def _get_value(self) -> EntityValue:
        return self._get_raw_sensor_value()


class RaritanPduInletSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduInletEntity, RaritanDeviceBinarySensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Inlet sensor backed sensor."""

    entity_description: RaritanPduInletBinarySensorEntityDescription


class RaritanPduOutletSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceBinarySensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduOutletBinarySensorEntityDescription


class RaritanPduSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduEntity, RaritanDeviceBinarySensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduBinarySensorEntityDescription


class RaritanPduOverCurrentProtectorSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanDeviceBinarySensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet sensor."""

    entity_description: RaritanPduOverCurrentProtectorBinarySensorEntityDescription
