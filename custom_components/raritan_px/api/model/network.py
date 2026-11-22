"""Raritan PDU API network models."""

from dataclasses import dataclass

from custom_components.raritan_px.api.model import RaritanModel
from custom_components.raritan_px.api.model.state import RaritanEnumState


@dataclass(kw_only=True)
class NetworkInterface(RaritanModel):
    """Representation of a Raritan PDU network interface."""

    name: str
    label: str
    type: NetworkInterfaceType
    enabled: bool
    state: NetworkInterfaceState
    mac_address: str


class NetworkInterfaceType(RaritanEnumState):
    """Network interface type enum."""

    ETHERNET = 0
    WLAN = 1
    BRIDGE = 2


class NetworkInterfaceState(RaritanEnumState):
    """Network interface type enum."""

    NOT_PRESENT = 0
    DOWN = 1
    NO_LINK = 2
    UP = 3
