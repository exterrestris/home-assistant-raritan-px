"""Raritan PDU switch entity descriptions."""

from dataclasses import dataclass
from typing import TypeVar

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription

from custom_components.raritan_px.entity.descriptions import (
    RaritanPduDeviceEntityDescription,
    RaritanPduOutletEntityDescription,
)


@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceSwitchEntityDescription(SwitchEntityDescription, RaritanPduDeviceEntityDescription):
    """Base class for a Raritan PDU outlet switch entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSwitchEntityDescription(
    RaritanPduDeviceSwitchEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet switch entity description."""


DESCRIPTIONS: tuple[RaritanPduOutletSwitchEntityDescription, ...] = (
    RaritanPduOutletSwitchEntityDescription(
        key="outlet_state",
        device_class=SwitchDeviceClass.OUTLET,
    ),
)
DESCRIPTIONS_MAP = {(type(desc), desc.key): desc for desc in DESCRIPTIONS}

SwitchDesc_co = TypeVar("SwitchDesc_co", bound="RaritanPduDeviceSwitchEntityDescription", covariant=True)


def get_entity_description[SwitchDesc_co: "RaritanPduDeviceSwitchEntityDescription"](
    desc_type: type[SwitchDesc_co], switch_name: str
) -> SwitchDesc_co:
    """Get the entity description instance matching the switch type and name."""
    if (desc_type, switch_name) in DESCRIPTIONS_MAP:
        return DESCRIPTIONS_MAP[(desc_type, switch_name)]  # pyright: ignore[reportReturnType, reportArgumentType]

    return desc_type(
        key=switch_name,
    )
