"""Raritan PDU sensor entities."""

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback

from custom_components.raritan_px.api.model.sensor import RaritanNumericSensor
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
    from custom_components.raritan_px.api.model.sensor import RaritanSensor
    from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
    )
    from custom_components.raritan_px.entity.sensor.descriptions import (
        RaritanDeviceSensorEntityDescription,
        RaritanPduInletSensorEntityDescription,
        RaritanPduOutletSensorEntityDescription,
        RaritanPduOverCurrentProtectorSensorEntityDescription,
        RaritanPduSensorEntityDescription,
    )


class RaritanDeviceSensorEntity(CoordinatedRaritanDeviceEntity, SensorEntity):
    """Base class of a Raritan PDU device sensor."""

    entity_description: RaritanDeviceSensorEntityDescription

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

    @classmethod
    def _entity_type(cls) -> str:
        return "sensor"

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        self._attr_native_value = self._get_value()

        return True


class RaritanDeviceAttributeBackedSensorEntity(
    CoordinatedRaritanDeviceAttributeBackedEntity, RaritanDeviceSensorEntity
):
    """Representation of a Raritan PDU device property backed sensor."""

    def _get_value(self) -> EntityValue:
        return self._get_device_attr_value()


class RaritanPduAttributeBackedSensorEntity(CoordinatedRaritanPduEntity, RaritanDeviceAttributeBackedSensorEntity):
    """Representation of a Raritan PDU Outlet attribute backed sensor."""

    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOutletAttributeBackedSensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceAttributeBackedSensorEntity
):
    """Representation of a Raritan PDU Outlet attribute backed sensor."""

    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduInletAttributeBackedSensorEntity(
    CoordinatedRaritanPduInletEntity, RaritanDeviceAttributeBackedSensorEntity
):
    """Representation of a Raritan PDU Inlet attribute backed sensor."""

    entity_description: RaritanPduInletSensorEntityDescription


class RaritanPduOverCurrentProtectorAttributeBackedSensorEntity(
    CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanDeviceAttributeBackedSensorEntity
):
    """Representation of a Raritan PDU Inlet attribute backed sensor."""

    entity_description: RaritanPduOverCurrentProtectorSensorEntityDescription


class RaritanDeviceSensorBackedSensorEntity(CoordinatedRaritanDeviceSensorBackedEntity, RaritanDeviceSensorEntity):
    """Representation of a Raritan device sensor backed sensor."""

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceSensorEntityDescription,
        sensor: RaritanSensor,
    ) -> None:
        """Initialise the entity."""
        super().__init__(device, hub, coordinator, description, sensor)

        if isinstance(self._sensor, RaritanNumericSensor) and description.suggested_display_precision is None:
            self._attr_suggested_display_precision = self._sensor.display_precision

    def _get_value(self) -> EntityValue:
        return self._get_sensor_value()

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        super()._async_update_attrs()

        # This check is here because Home Assistant only supports last_reset with a state class of TOTAL, however the
        # Raritan JSON-RPC API only supplies a last reset time for accumlating numeric sensors which best map to a state
        # class of TOTAL_INCREASING
        if self.entity_description.state_class == SensorStateClass.TOTAL and self._sensor.last_reset is not None:
            self._attr_last_reset = self._sensor.last_reset

        if self._sensor.unit is not None:
            self._attr_native_unit_of_measurement = self._sensor.unit

        return True


class RaritanPduInletSensorBackedSensorEntity(CoordinatedRaritanPduInletEntity, RaritanDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Inlet sensor backed sensor."""

    entity_description: RaritanPduInletSensorEntityDescription


class RaritanPduOutletSensorBackedSensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceSensorBackedSensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduSensorBackedSensorEntity(CoordinatedRaritanPduEntity, RaritanDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOverCurrentProtectorSensorBackedSensorEntity(
    CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanDeviceSensorBackedSensorEntity
):
    """Representation of a Raritan PDU Outlet sensor."""

    entity_description: RaritanPduOverCurrentProtectorSensorEntityDescription
