from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntityDescription

from custom_components.raritan_px.entity.description import RaritanPduDeviceEntityDescription, RaritanPduOutletEntityDescription


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
