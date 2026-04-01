from typing import TypeVar

from homeassistant.components.switch import SwitchDeviceClass

from custom_components.raritan_px.entity.switch.description import RaritanPduDeviceSwitchEntityDescription
from custom_components.raritan_px.entity.switch.description import (
    RaritanPduOutletSwitchEntityDescription,
)


DESCRIPTIONS: tuple[RaritanPduOutletSwitchEntityDescription, ...] = (
    RaritanPduOutletSwitchEntityDescription(
        key="outlet_state",
        device_class=SwitchDeviceClass.OUTLET,
    ),
)
DESCRIPTIONS_MAP = { (type(desc), desc.key) : desc for desc in DESCRIPTIONS}

T = TypeVar('T', bound="RaritanPduDeviceSwitchEntityDescription", covariant=True)

def get_entity_description(desc_type: type[T], switch_name: str) -> T:
    if (desc_type, switch_name) in DESCRIPTIONS_MAP:
        return DESCRIPTIONS_MAP[(desc_type, switch_name)] # pyright: ignore[reportReturnType, reportArgumentType]

    return desc_type(
        key=switch_name,
    )
