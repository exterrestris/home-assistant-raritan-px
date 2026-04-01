from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback

from custom_components.raritan_px.entity.sensor.description import (
    RaritanPduSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
    RaritanPduInletSensorEntityDescription,
    RaritanPduDeviceSensorEntityDescription,
    SensorEntityValue,
)
from custom_components.raritan_px.entity.description import (
    RaritanPduDeviceEntityDescription,
)
from custom_components.raritan_px.entity import (
    CoordinatedRaritanPduDeviceEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduInletEntity,
)
from custom_components.raritan_px.api.model.sensor import RaritanSensor
from custom_components.raritan_px.api.model.device import RaritanPdu, RaritanPduDevice
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator

class RaritanPduDeviceSensorEntity(CoordinatedRaritanPduDeviceEntity, SensorEntity):
    """Base class of a Raritan PDU device sensor."""

    entity_description: RaritanPduDeviceSensorEntityDescription

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceEntityDescription,
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

    def _get_value(self) -> SensorEntityValue:
        raise NotImplementedError

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._get_value()

        if value is not None:
            if self.entity_description.convert_fn is not None:
                value = self.entity_description.convert_fn(value)

        self._attr_native_value = value

        return True


class RaritanPduDevicePropertyBackedSensorEntity(RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU device property backed sensor."""

    _property: str

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceEntityDescription,
            property: str
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._property = property

    def _get_unique_id(self) -> str:
        return f"{self._device.device_id}_prop_{self.entity_description.key}"

    def _get_value(self) -> SensorEntityValue:
        return getattr(self._device, self._property)

class RaritanPduPropertyBackedSensorEntity(CoordinatedRaritanPduEntity, RaritanPduDevicePropertyBackedSensorEntity):
    """Representation of a Raritan PDU Outlet property backed sensor."""

    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOutletPropertyBackedSensorEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDevicePropertyBackedSensorEntity):
    """Representation of a Raritan PDU Outlet property backed sensor."""

    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduInletPropertyBackedSensorEntity(CoordinatedRaritanPduInletEntity, RaritanPduDevicePropertyBackedSensorEntity):
    """Representation of a Raritan PDU Inlet property backed sensor."""

    entity_description: RaritanPduInletSensorEntityDescription


class RaritanPduDeviceSensorBackedSensorEntity(RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU device sensor backed sensor."""

    _sensor: RaritanSensor

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceEntityDescription,
            sensor: RaritanSensor
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._sensor = sensor

    def _get_value(self) -> SensorEntityValue:
        return self._sensor.value

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        super()._async_update_attrs()

        if self._sensor.precision is not None:
            self._attr_suggested_display_precision = self._sensor.precision

        # This check is here because Home Assistant only supports last_reset with a
        # state class of TOTAL, however the Raritan JSON-RPC API only supplies a last
        # reset time for accumlating numeric sensors which best map to a state class
        # of TOTAL_INCREASING
        if self.entity_description.state_class == SensorStateClass.TOTAL:
            if self._sensor.last_reset is not None:
                self._attr_last_reset = self._sensor.last_reset

        if self._sensor.unit is not None:
            self._attr_native_unit_of_measurement = self._sensor.unit

        return True


class RaritanPduSensorBackedSensorEntity(CoordinatedRaritanPduEntity, RaritanPduDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduSensorEntityDescription


class RaritanPduOutletSensorBackedSensorEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Outlet sensor backed sensor."""

    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduInletSensorBackedSensorEntity(CoordinatedRaritanPduInletEntity, RaritanPduDeviceSensorBackedSensorEntity):
    """Representation of a Raritan PDU Inlet sensor backed sensor."""

    entity_description: RaritanPduInletSensorEntityDescription
