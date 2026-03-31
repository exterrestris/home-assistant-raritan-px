from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import SensorEntityDescription
from custom_components.raritan_px.entity.description import (
    RaritanPduEntityDescription,
    RaritanPduOutletEntityDescription,
    RaritanPduInletEntityDescription,
    RaritanPduDeviceEntityDescription,
)

type SensorEntityValue = StateType | date | datetime | Decimal

@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceSensorEntityDescription(
    SensorEntityDescription, RaritanPduDeviceEntityDescription
):
    """Base class for a Raritan PDU device sensor entity description."""

    convert_fn: Callable[[Any], SensorEntityValue | None] | None = None


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduInletEntityDescription
):
    """Base class for a Raritan PDU inlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduOutletEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduSensorEntityDescription(
    RaritanPduDeviceSensorEntityDescription, RaritanPduEntityDescription
):
    """Base class for a Raritan PDU sensor entity description."""
