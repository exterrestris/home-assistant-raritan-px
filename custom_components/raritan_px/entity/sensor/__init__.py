"""Raritan PDU sensor entities."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.raritan_px.api.model.sensor import RaritanNumericSensor
from custom_components.raritan_px.const import DOMAIN
from custom_components.raritan_px.entity import (
    CoordinatedRaritanDeviceAttributeBackedEntity,
    CoordinatedRaritanDeviceEntity,
    CoordinatedRaritanDeviceSensorBackedEntity,
    CoordinatedRaritanEntity,
    CoordinatedRaritanIntegrationEntity,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduInletEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduOverCurrentProtectorEntity,
    EntityValue,
)

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo

    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.sensor import RaritanSensor
    from custom_components.raritan_px.coordinator import RaritanApiDataUpdateCoordinator, RaritanDataUpdateCoordinator
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
        RaritanEntityDescription,
    )
    from custom_components.raritan_px.entity.sensor.descriptions import (
        RaritanDeviceSensorEntityDescription,
        RaritanPduInletSensorEntityDescription,
        RaritanPduOutletSensorEntityDescription,
        RaritanPduOverCurrentProtectorSensorEntityDescription,
        RaritanPduSensorEntityDescription,
    )


class RaritanSensorEntity(CoordinatedRaritanEntity, SensorEntity):
    """Base class of a Raritan sensor."""

    entity_description: RaritanPduSensorEntityDescription

    def __init__(
        self,
        coordinator: RaritanDataUpdateCoordinator,
        *,
        context: Any = None,
        description: RaritanEntityDescription,
        device: RaritanDevice | None,
        hub: DeviceEntry | None,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, context=context, device=device, hub=hub, description=description)

    def _get_value(self) -> EntityValue:
        raise NotImplementedError

    @classmethod
    def _entity_type(cls) -> str:
        return "sensor"

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        if self.entity_description.is_dynamic and self.coordinator.firmware_update_in_progress:
            return False

        self._attr_native_value = self._get_value()

        return True


class RaritanDeviceSensorEntity(CoordinatedRaritanDeviceEntity, RaritanSensorEntity):
    """Base class of a Raritan PDU device sensor."""

    entity_description: RaritanDeviceSensorEntityDescription

    def __init__(
        self,
        coordinator: RaritanApiDataUpdateCoordinator,
        *,
        description: RaritanDeviceEntityDescription,
        device: RaritanDevice,
        hub: DeviceEntry,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, device=device, hub=hub, description=description)


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
        coordinator: RaritanApiDataUpdateCoordinator,
        *,
        description: RaritanDeviceSensorEntityDescription,
        device: RaritanDevice,
        hub: DeviceEntry,
        sensor: RaritanSensor,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, device=device, hub=hub, description=description, sensor=sensor)

        if isinstance(self._sensor, RaritanNumericSensor) and description.suggested_display_precision is None:
            self._attr_suggested_display_precision = self._sensor.display_precision

        if self._sensor.unit is not None:
            self._attr_native_unit_of_measurement = self._sensor.unit

    def _get_value(self) -> EntityValue:
        return self._get_sensor_value()

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        if not super()._async_update_attrs():
            return False

        # This check is here because Home Assistant only supports last_reset with a state class of TOTAL, however the
        # Raritan JSON-RPC API only supplies a last reset time for accumlating numeric sensors which best map to a state
        # class of TOTAL_INCREASING
        if self.entity_description.state_class == SensorStateClass.TOTAL and self._sensor.last_reset is not None:
            self._attr_last_reset = self._sensor.last_reset

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


class RaritanIntegrationCoordinatorSensorEntity(CoordinatedRaritanIntegrationEntity, RaritanSensorEntity):
    """Representation of a Raritan Integration sensor."""

    def _get_value(self) -> EntityValue:
        return self._get_attr_value(self.coordinator)

    def _get_device_info(self) -> DeviceInfo | None:
        return None

    def _get_unique_id(self) -> str:
        return self._build_unique_id(DOMAIN, self.entity_description.key)

    @classmethod
    def _entity_source(cls) -> str:
        return "integration"
