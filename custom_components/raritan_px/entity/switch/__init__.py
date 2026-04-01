from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback

from custom_components.raritan_px.api.model.device import RaritanPdu, RaritanPduDevice, RaritanPduOutlet
from custom_components.raritan_px.api.model.device.states import OutletPowerState
from custom_components.raritan_px.api.model.sensor import RaritanSwitch
from custom_components.raritan_px.api.model.sensor.states import OnOff
from custom_components.raritan_px.coordinator import RaritanPduDataUpdateCoordinator
from custom_components.raritan_px.entity import CoordinatedRaritanPduDeviceEntity, CoordinatedRaritanPduOutletEntity
from custom_components.raritan_px.entity.description import RaritanPduDeviceEntityDescription
from custom_components.raritan_px.entity.switch.description import RaritanPduDeviceSwitchEntityDescription, RaritanPduOutletSwitchEntityDescription


class RaritanPduDeviceSwitchEntity(CoordinatedRaritanPduDeviceEntity, SwitchEntity):
    """Representation of a Raritan PDU Outlet switch."""

    _switch: RaritanSwitch
    entity_description: RaritanPduDeviceSwitchEntityDescription

    def __init__(
            self,
            device: RaritanPduDevice,
            pdu: RaritanPdu,
            coordinator: RaritanPduDataUpdateCoordinator,
            description: RaritanPduDeviceEntityDescription,
            switch: RaritanSwitch
        ) -> None:
        super().__init__(device, pdu, coordinator, description)

        self._switch = switch

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        raise NotImplementedError

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        raise NotImplementedError

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
