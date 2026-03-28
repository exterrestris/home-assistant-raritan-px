"""Support for RaritanPdu switch entities."""

from __future__ import annotations
from typing import Any, TypeVar
from itertools import product
from more_itertools import flatten
from dataclasses import dataclass
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)

from .api.model.device import (
    RaritanPduDevice,
    RaritanPduOutlet,
    RaritanPdu,
)
from .api.model.device.states import OutletPowerState
from .api.model.sensor import RaritanSwitch
from .api.model.sensor.states import OnOff
from .coordinator import (
    RaritanPduConfigEntry,
    RaritanPduData,
    RaritanPduDataUpdateCoordinator,
)
from .entity import (
    RaritanPduDeviceEntityDescription,
    RaritanPduOutletEntityDescription,
    CoordinatedRaritanPduDeviceEntity,
    CoordinatedRaritanPduOutletEntity,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceSwitchEntityDescription(
    SwitchEntityDescription, RaritanPduDeviceEntityDescription
):
    """Base class for a Raritan PDU outlet switch entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSwitchEntityDescription(
    RaritanPduDeviceSwitchEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet switch entity description."""


SWITCH_DESCRIPTIONS: tuple[RaritanPduOutletSwitchEntityDescription, ...] = (
    RaritanPduOutletSwitchEntityDescription(
        key="outlet_state",
        device_class=SwitchDeviceClass.OUTLET,
    ),
)

SENSOR_DESCRIPTIONS_MAP = { (type(desc), desc.key) : desc for desc in SWITCH_DESCRIPTIONS}

T = TypeVar('T', bound="RaritanPduDeviceSwitchEntityDescription", covariant=True)

def get_entity_description(type: type[T], key: str) -> T:
    if (type, key) in SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_DESCRIPTIONS_MAP[(type, key)] # pyright: ignore[reportReturnType, reportArgumentType]

    return type(
        key=key,
    )

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RaritanPduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    data: RaritanPduData = config_entry.runtime_data
    coordinator: RaritanPduDataUpdateCoordinator = data.coordinator
    pdu: RaritanPdu = coordinator.pdu

    if pdu.has_switchable_outlets:
        async_add_entities(
            RaritanPduOutletSwitchEntity(
                outlet,
                pdu,
                coordinator,
                get_entity_description(RaritanPduOutletSwitchEntityDescription, switch),
            )
            for outlet, switch in list(
                flatten([list(product([outlet], switchs)) for (outlet, switchs) in [(outlet, [switch for switch, _ in outlet.available_switches]) for outlet in pdu.outlets]])
            )
        )

class RaritanPduDeviceSwitchEntity(CoordinatedRaritanPduDeviceEntity, SwitchEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _switch: RaritanSwitch
    entity_description: RaritanPduDeviceSwitchEntityDescription

    def __init__(self, device: RaritanPduDevice, pdu: RaritanPdu, coordinator: RaritanPduDataUpdateCoordinator, description: RaritanPduDeviceEntityDescription) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._switch = self._device.sensors[self.entity_description.key] # pyright: ignore[reportAttributeAccessIssue]


    @callback
    def _async_update_attrs(self) -> bool:
        """Update the entity's attributes."""
        self._attr_is_on = self._switch.state == OnOff.ON if self._switch.state is not None else None

        return True


class RaritanPduOutletSwitchEntity(CoordinatedRaritanPduOutletEntity, RaritanPduDeviceSwitchEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _device: RaritanPduOutlet
    entity_description: RaritanPduOutletSwitchEntityDescription

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.set_outlet_power_state(self._device, OutletPowerState.ON)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.set_outlet_power_state(self._device, OutletPowerState.OFF)
        await self.coordinator.async_request_refresh()
