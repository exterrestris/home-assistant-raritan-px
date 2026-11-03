"""Raritan PDU sensor entities."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback

from custom_components.raritan_px.entity import (
    CoordinatedRaritanDeviceEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduInletEntity,
    CoordinatedRaritanPduOutletEntity,
)

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.api.model.sensor import RaritanSensor
    from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator
    from custom_components.raritan_px.entity.binary_sensor.descriptions import (
        BinarySensorEntityValue,
        RaritanDeviceBinarySensorEntityDescription,
        RaritanPduBinarySensorEntityDescription,
        RaritanPduInletBinarySensorEntityDescription,
        RaritanPduOutletBinarySensorEntityDescription,
    )
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
    )


class RaritanDeviceBinarySensorEntity(CoordinatedRaritanDeviceEntity, BinarySensorEntity):
    """Base class of a Raritan PDU device sensor."""

    _sensor: RaritanSensor
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

    def _get_value(self) -> BinarySensorEntityValue:
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


class RaritanDeviceSensorBackedBinarySensorEntity(RaritanDeviceBinarySensorEntity):
    """Representation of a Raritan device sensor backed sensor."""

    _sensor: RaritanSensor

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
        sensor: RaritanSensor,
    ) -> None:
        """Initialise the entity."""
        super().__init__(device, hub, coordinator, description)

        self._sensor = sensor

    def _get_value(self) -> BinarySensorEntityValue:
        return self._sensor.value


class RaritanPduInletSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduInletEntity, RaritanDeviceSensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Inlet sensor backed sensor."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletBinarySensorEntityDescription


class RaritanPduOutletSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceSensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletBinarySensorEntityDescription


class RaritanPduSensorBackedBinarySensorEntity(
    CoordinatedRaritanPduEntity, RaritanDeviceSensorBackedBinarySensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    _device: RaritanPdu
    entity_description: RaritanPduBinarySensorEntityDescription
