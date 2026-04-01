from dataclasses import dataclass
from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class RaritanPduDeviceEntityDescription(EntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletEntityDescription(RaritanPduDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletEntityDescription(RaritanPduDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""

@dataclass(frozen=True, kw_only=True)
class RaritanPduOverCurrentProtectorEntityDescription(RaritanPduDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduEntityDescription(RaritanPduDeviceEntityDescription):
    """Base class for a Raritan PDU entity description."""
