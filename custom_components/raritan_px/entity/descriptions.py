"""Raritan PDU base entity descriptions."""

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceEntityDescription(EntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOverCurrentProtectorEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduEntityDescription(RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""
