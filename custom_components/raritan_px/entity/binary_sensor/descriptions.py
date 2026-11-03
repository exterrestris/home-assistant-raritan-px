"""Raritan PDU sensor entity descriptions."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.helpers.typing import StateType

from custom_components.raritan_px.api.model.sensor.state import (
    NormalAlarmed,
    OkFaulted,
    OnOff,
    RaritanSensorState,
)
from custom_components.raritan_px.entity.descriptions import (
    RaritanDeviceEntityDescription,
    RaritanPduEntityDescription,
    RaritanPduInletEntityDescription,
    RaritanPduOutletEntityDescription,
)

type BinarySensorEntityValue = StateType | date | datetime | Decimal


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceBinarySensorEntityDescription(BinarySensorEntityDescription, RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU device sensor entity description."""

    has_entity_name: bool = True
    on_value: RaritanSensorState


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletBinarySensorEntityDescription(
    RaritanDeviceBinarySensorEntityDescription, RaritanPduInletEntityDescription
):
    """Base class for a Raritan PDU inlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletBinarySensorEntityDescription(
    RaritanDeviceBinarySensorEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduBinarySensorEntityDescription(RaritanDeviceBinarySensorEntityDescription, RaritanPduEntityDescription):
    """Base class for a Raritan PDU sensor entity description."""


SENSOR_BACKED_SENSOR_DESCRIPTIONS: tuple[RaritanDeviceBinarySensorEntityDescription, ...] = (
    RaritanPduBinarySensorEntityDescription(
        key="power_supply_status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_value=NormalAlarmed.ALARMED,
        translation_key="pdu_power_supply_status",
    ),
    RaritanPduOutletBinarySensorEntityDescription(
        key="outlet_state",
        device_class=BinarySensorDeviceClass.POWER,
        on_value=OnOff.ON,
        translation_key="outlet_outlet_state",
    ),
    RaritanPduInletBinarySensorEntityDescription(
        key="power_quality",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_value=NormalAlarmed.ALARMED,
        translation_key="inlet_power_quality",
    ),
    RaritanPduInletBinarySensorEntityDescription(
        key="surge_protector_status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_value=OkFaulted.FAULT,
        translation_key="inlet_surge_protector_status",
    ),
)
SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP = {(type(desc), desc.key): desc for desc in SENSOR_BACKED_SENSOR_DESCRIPTIONS}

SensorDesc_co = TypeVar("SensorDesc_co", bound="RaritanDeviceBinarySensorEntityDescription", covariant=True)


def get_entity_description[SensorDesc_co: "RaritanDeviceBinarySensorEntityDescription"](
    desc_type: type[SensorDesc_co], sensor_name: str
) -> SensorDesc_co | None:
    """Get the entity description instance matching the sensor type and name."""

    def default_name(name: str = sensor_name) -> str:
        return name.replace("_", " ").replace(":", " ").title()

    if (desc_type, sensor_name) in SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP[(desc_type, sensor_name)]  # pyright: ignore[reportReturnType, reportArgumentType]

    if ":" in sensor_name:
        generic_name, idx = sensor_name.split(":")

        if (desc_type, generic_name) in SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP:
            desc = SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP[(desc_type, generic_name)]  # pyright: ignore[reportArgumentType]

            def formatted_name() -> str:
                if type(desc.name) is str:
                    return desc.name.format(int(idx) + 1)

                return f"{default_name(generic_name)} {int(idx) + 1}"

            if type(desc.translation_key) is str:
                merge = {"translation_placeholders": {"idx": str(int(idx) + 1)}}
            else:
                merge = {"name": formatted_name()}

            return desc_type(
                **(asdict(desc) | {"key": sensor_name} | merge)  # pyright: ignore[reportReturnType, reportArgumentType]
            )

    return None
