"""Raritan PDU base entity descriptions."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import EntityDescription

if TYPE_CHECKING:
    from collections.abc import Callable

    from custom_components.raritan_px.api.model.device.pdu import RaritanPdu
    from custom_components.raritan_px.api.model.device.pdu.inlet import RaritanPduInlet
    from custom_components.raritan_px.api.model.device.pdu.ocp import RaritanPduOverCurrentProtector
    from custom_components.raritan_px.api.model.device.pdu.outlet import RaritanPduOutlet
    from custom_components.raritan_px.entity import EntityValue


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceEntityDescription(EntityDescription):
    """Base class for a Raritan PDU entity description."""

    convert_fn: Callable[[Any], EntityValue | None] | None = None


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""

    is_available_for: Callable[[RaritanPduInlet], bool] = field(default=lambda _: True)


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""

    is_available_for: Callable[[RaritanPduOutlet], bool] = field(default=lambda _: True)


@dataclass(frozen=True, kw_only=True)
class RaritanPduOverCurrentProtectorEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""

    is_available_for: Callable[[RaritanPduOverCurrentProtector], bool] = field(default=lambda _: True)


@dataclass(frozen=True, kw_only=True)
class RaritanPduEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""

    is_available_for: Callable[[RaritanPdu], bool] = field(default=lambda _: True)
