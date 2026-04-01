from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback

from custom_components.raritan_px.entity.sensor.description import (
    RaritanPduSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
    RaritanPduInletSensorEntityDescription,
    RaritanPduOverCurrentProtectorSensorEntityDescription,
    RaritanPduDeviceSensorEntityDescription,
)
from custom_components.raritan_px.entity.description import (
    RaritanPduDeviceEntityDescription,
)
from custom_components.raritan_px.entity import (
    CoordinatedRaritanPduDeviceEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduInletEntity,
    CoordinatedRaritanPduOverCurrentProtectorEntity,
)
from custom_components.raritan_px.api.model.sensor import RaritanSensor
from custom_components.raritan_px.api.model.device import (
    RaritanPdu,
    RaritanPduDevice,
    RaritanPduOutlet,
    RaritanPduInlet,
    RaritanPduOverCurrentProtector,
)
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator

class RaritanPduDeviceSensorEntity(CoordinatedRaritanPduDeviceEntity, SensorEntity):
    """Representation of a Raritan PDU device sensor."""

    _sensor: RaritanSensor
    entity_description: RaritanPduDeviceSensorEntityDescription

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceSensorEntityDescription,
            sensor: RaritanSensor
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._sensor = sensor

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._sensor.value

        if value is not None:
            if self.entity_description.convert_fn is not None:
                value = self.entity_description.convert_fn(value)

            if self._sensor.precision is not None:
                self._attr_suggested_display_precision = self._sensor.precision

        self._attr_native_value = value

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


class RaritanPduInletSensorEntity(CoordinatedRaritanPduInletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Inlet sensor."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletSensorEntityDescription


class RaritanPduOutletSensorEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Outlet sensor."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription


class RaritanPduOverCurrentProtectorSensorEntity(CoordinatedRaritanPduOverCurrentProtectorEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Overcurrent Protector sensor."""

    _device: RaritanPduOverCurrentProtector
    entity_description: RaritanPduOverCurrentProtectorSensorEntityDescription


class RaritanPduSensorEntity(CoordinatedRaritanPduEntity, RaritanPduDeviceSensorEntity):
    """Representation of a Raritan PDU Outlet sensor."""

    _device: RaritanPdu
    entity_description: RaritanPduSensorEntityDescription
