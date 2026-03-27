"""Support for RaritanPdu switch entities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from .api import RaritanPdu, RaritanPduOutlet
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from .entity import (
    RaritanPduEntityDescription,
    RaritanPduOutletEntityDescription,
    RaritanPduInletEntityDescription,
    CoordinatedRaritanPduEntity,
    CoordinatedRaritanPduOutletEntity,
    CoordinatedRaritanPduInletEntity,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RaritanPduSensorEntityDescription(
    SensorEntityDescription, RaritanPduEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSensorEntityDescription(
    SensorEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduInletSensorEntityDescription(
    SensorEntityDescription, RaritanPduInletEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    if pdu.has_metered_outlets:
        async_add_entities(
            RaritanPduOutletSensorEntity(
                outlet,
                pdu,
                coordinator,
                RaritanPduOutletSensorEntityDescription(
                    key=sensor,
                ),
            )
            for outlet, sensor in list(
                flatten([list(product([outlet], sensors)) for (outlet, sensors) in [(outlet, [sensor for sensor, _ in outlet.available_sensors]) for outlet in pdu.outlets]])
            )
        )


class RaritanPduOutletSensorEntity(CoordinatedRaritanPduOutletEntity, SensorEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSensorEntityDescription

    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        value = self._device.sensors[self.entity_description.key].reading # pyright: ignore[reportAttributeAccessIssue]
        self._attr_native_value = value
        return True
