"""Raritan PDU sensor entities."""

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback

from custom_components.raritan_px.api.model.device import RaritanDevice
from custom_components.raritan_px.api.model.sensor.state import RaritanSensorState
from custom_components.raritan_px.entity import (
    CoordinatedRaritanDeviceEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduInletEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduOverCurrentProtectorEntity,
)

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
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
        SensorEntityValue,
    )


class RaritanDeviceSensorEntity(CoordinatedRaritanDeviceEntity, SensorEntity):
    """Base class of a Raritan PDU device sensor."""

    _sensor: RaritanSensor
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

    def _get_value(self) -> SensorEntityValue:
        raise NotImplementedError

    def _entity_type(self) -> str:
        return "sensor"

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._get_value()

        if value is not None:
            if self.entity_description.convert_fn is not None:
                value = self.entity_description.convert_fn(value)
            elif isinstance(value, RaritanSensorState):
                value = value.friendly_name()

        self._attr_native_value = value

        return True


class RaritanDeviceAttributeBackedSensorEntity(RaritanDeviceSensorEntity):
    """Representation of a Raritan PDU device property backed sensor."""

    _attr: str

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
        attribute: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(device, hub, coordinator, description)

        self._attr = attribute

    def _get_unique_id(self) -> str:
        return f"{self._device.device_id}_prop_{self.entity_description.key}"

    def _get_value(self) -> SensorEntityValue:
        device = self._device
        path = self._attr.split(".")
        attr = path.pop()

        for elm in path:
            if not isinstance(device := getattr(device, elm), RaritanDevice):
                return None

        return getattr(device, attr)


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


class RaritanDeviceSensorBackedSensorEntity(RaritanDeviceSensorEntity):
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

    def _get_value(self) -> SensorEntityValue:
        return self._sensor.value

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        super()._async_update_attrs()

        if self._sensor.precision is not None:
            self._attr_suggested_display_precision = self._sensor.precision

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

    _device: RaritanPduInlet
    entity_description: RaritanPduInletSensorEntityDescription


class RaritanPduOutletSensorBackedSensorEntity(
    CoordinatedRaritanPduOutletEntity, RaritanDeviceSensorBackedSensorEntity
):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduSensorBackedSensorEntity(CoordinatedRaritanPduEntity, RaritanDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    _device: RaritanPdu
    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOverCurrentProtectorSensorBackedSensorEntity(
    CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanDeviceSensorBackedSensorEntity
):
    """Representation of a Raritan PDU Outlet sensor."""

    _device: RaritanPduOverCurrentProtector
    entity_description: RaritanPduOverCurrentProtectorSensorEntityDescription
