"""Raritan PDU base entities."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.raritan_px.api import RaritanEnum
from custom_components.raritan_px.api.model import RaritanModel
from custom_components.raritan_px.const import DOMAIN
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator

if TYPE_CHECKING:
    from custom_components.raritan_px.api.model.device import (
        RaritanDevice,
        RaritanEnergyDevice,
    )
    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.api.model.sensor import RaritanSensor
    from custom_components.raritan_px.entity.descriptions import (
        RaritanDeviceEntityDescription,
        RaritanPduEntityDescription,
        RaritanPduInletEntityDescription,
        RaritanPduOutletEntityDescription,
        RaritanPduOverCurrentProtectorEntityDescription,
    )

_LOGGER = logging.getLogger(__name__)

type EntityValue = StateType | date | datetime | Decimal


class CoordinatedRaritanDeviceEntity(CoordinatorEntity[RaritanPduDataUpdateCoordinator], ABC):
    """Common base class for all coordinated raritan device entities."""

    _attr_has_entity_name = True
    _device: RaritanDevice
    _pdu: RaritanPdu
    _hub: DeviceEntry

    entity_description: RaritanDeviceEntityDescription

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator, context=(device.device_id, description.key))

        self.entity_description = description
        self._device = device
        self._pdu = coordinator.pdu
        self._hub = hub

        self._attr_device_info = self._get_device_info()
        self._attr_unique_id = self._get_unique_id()

        _LOGGER.debug("Created %s %s for %s", description.key, self._entity_type(), device.device_id)

    def _get_unique_id(self) -> str:
        return f"{self._device.device_id}_{self.entity_description.key}"

    @abstractmethod
    def _entity_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _get_device_info(self) -> DeviceInfo:
        raise NotImplementedError

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> bool:
        """
        Platforms implement this to update the entity internals.

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


class CoordinatedRaritanDeviceSensorBackedEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan device entities backed by a device sensor."""

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

    def _get_raw_sensor_value(self) -> Any:
        return self._sensor.value

    def _get_sensor_value(self) -> EntityValue:
        value = self._get_raw_sensor_value()

        if value is not None and self.entity_description.convert_fn is not None:
            value = self.entity_description.convert_fn(value)

        if isinstance(value, RaritanEnum):
            value = value.friendly_name()

        return value


class CoordinatedRaritanDeviceAttributeBackedEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan device entities backed by a device attribute."""

    _device_attr: str
    _model: RaritanModel | None

    def __init__(
        self,
        device: RaritanDevice,
        hub: DeviceEntry,
        coordinator: RaritanPduDataUpdateCoordinator,
        description: RaritanDeviceEntityDescription,
        *,
        model: RaritanModel | None = None,
    ) -> None:
        """Initialise the entity."""
        self._device_attr = description.key
        self._model = model

        super().__init__(device, hub, coordinator, description)

    def _get_unique_id(self) -> str:
        return re.sub(r"__+", "_", re.sub(r"[\.\[\]]", "_", f"{self._device.device_id}_prop_{self._device_attr}"))

    def _get_raw_device_attr_value(self) -> Any:
        source = self._model or self._device
        path = self._device_attr.split(".")
        attr = path.pop()

        try:
            for elm in path:
                if m := re.fullmatch(r"(?P<elm>[a-z0-9_]+)\[(?P<key>[a-z0-9_]+)\]", elm):
                    source = getattr(source, m.group("elm"))
                    source = source[m.group("key")]
                    continue

                if not isinstance(source := getattr(source, elm), RaritanModel):
                    return None

            return getattr(source, attr)
        except AttributeError, KeyError, ValueError:
            return None

    def _get_device_attr_value(self) -> EntityValue:
        value = self._get_raw_device_attr_value()

        if value is not None and self.entity_description.convert_fn is not None:
            value = self.entity_description.convert_fn(value)

        if isinstance(value, RaritanEnum):
            value = value.friendly_name()

        return value


class CoordinatedRaritanPduEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu based entities."""

    _device: RaritanPdu
    entity_description: RaritanPduEntityDescription

    def _get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.device_id))},
            manufacturer=self._device.manufacturer,
            model=self._device.device_model,
            name=self._device.device_name,
            configuration_url=self._device.url,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._device.mac_address)},
        )


class CoordinatedRaritanEnergyDeviceEntity(CoordinatedRaritanDeviceEntity, ABC):
    """Common base class for all coordinated raritan energy device based entities."""

    _device: RaritanEnergyDevice
    entity_description: RaritanDeviceEntityDescription

    def _get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.device_id))},
            manufacturer=self._device.pdu.manufacturer,
            model=self._device.device_model,
            name=self._device.device_name,
            via_device_id=self._hub.id,
        )


class CoordinatedRaritanPduOutletEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu outlet based entities."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletEntityDescription


class CoordinatedRaritanPduInletEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu inlet based entities."""

    _device: RaritanPduInlet
    entity_description: RaritanPduInletEntityDescription


class CoordinatedRaritanPduOverCurrentProtectorEntity(CoordinatedRaritanEnergyDeviceEntity, ABC):
    """Common base class for all coordinated raritan pdu overcurrent protector based entities."""

    _device: RaritanPduOverCurrentProtector
    entity_description: RaritanPduOverCurrentProtectorEntityDescription
