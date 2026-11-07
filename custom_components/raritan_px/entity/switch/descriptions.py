"""Raritan PDU switch entity descriptions."""

from dataclasses import dataclass

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription

from custom_components.raritan_px.entity.descriptions import (
    RaritanDeviceEntityDescription,
    RaritanPduOutletEntityDescription,
)


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceSwitchEntityDescription(SwitchEntityDescription, RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU outlet switch entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSwitchEntityDescription(RaritanDeviceSwitchEntityDescription, RaritanPduOutletEntityDescription):
    """Base class for a Raritan PDU outlet switch entity description."""


DESCRIPTIONS: tuple[RaritanDeviceSwitchEntityDescription, ...] = (
    RaritanPduOutletSwitchEntityDescription(
        key="outlet_state",
        device_class=SwitchDeviceClass.OUTLET,
    ),
)
DESCRIPTIONS_MAP = {(type(desc), desc.key): desc for desc in DESCRIPTIONS}


def get_entity_description[SwitchDesc: "RaritanDeviceSwitchEntityDescription"](
    desc_type: type[SwitchDesc], switch_name: str
) -> SwitchDesc | None:
    """Get the entity description instance matching the switch type and name."""
    if (desc_type, switch_name) in DESCRIPTIONS_MAP:
        return DESCRIPTIONS_MAP[(desc_type, switch_name)]  # pyright: ignore[reportReturnType, reportArgumentType]

    return None
