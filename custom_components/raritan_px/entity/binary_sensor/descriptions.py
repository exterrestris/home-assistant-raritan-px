"""Raritan PDU sensor entity descriptions."""

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.const import EntityCategory

from custom_components.raritan_px.entity.descriptions import (
    RaritanDeviceEntityDescription,
    RaritanPduEntityDescription,
    RaritanPduInletEntityDescription,
    RaritanPduOutletEntityDescription,
)


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceBinarySensorEntityDescription(BinarySensorEntityDescription, RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU device sensor entity description."""

    on_value: Any = field(default=True)


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
class RaritanPduOverCurrentProtectorBinarySensorEntityDescription(
    RaritanDeviceBinarySensorEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU OCP sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduBinarySensorEntityDescription(RaritanDeviceBinarySensorEntityDescription, RaritanPduEntityDescription):
    """Base class for a Raritan PDU sensor entity description."""


PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduBinarySensorEntityDescription, ...] = (
    RaritanPduBinarySensorEntityDescription(
        key="has_switchable_outlets",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_has_switchable_outlets",
        entity_registry_enabled_default=False,
    ),
    RaritanPduBinarySensorEntityDescription(
        key="has_metered_outlets",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_has_metered_outlets",
        entity_registry_enabled_default=False,
    ),
)
