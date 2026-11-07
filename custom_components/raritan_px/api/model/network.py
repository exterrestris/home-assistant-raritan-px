"""Raritan PDU API network models."""

from dataclasses import dataclass
from enum import IntEnum

from raritan.rpc.net import InterfaceOpState, InterfaceType

from custom_components.raritan_px.api import RaritanEnum
from custom_components.raritan_px.api.model import RaritanModel


@dataclass(kw_only=True)
class NetworkInterface(RaritanModel):
    """Representation of a Raritan PDU network interface."""

    name: str
    label: str
    type: NetworkInterfaceType
    enabled: bool
    state: NetworkInterfaceState
    mac_address: str


class NetworkEnum(RaritanEnum):
    """Base network enum."""


class NetworkInterfaceType(NetworkEnum, IntEnum):
    """Network interface type enum."""

    ETHERNET = 0
    WLAN = 1
    BRIDGE = 2


class NetworkInterfaceState(NetworkEnum, IntEnum):
    """Network interface type enum."""

    NOT_PRESENT = 0
    DOWN = 1
    NO_LINK = 2
    UP = 3


NETWORK_ENUM_TYPE_VALUE_MAPPING: dict[type[NetworkEnum], dict[int, NetworkEnum]] = {
    NetworkInterfaceType: {
        InterfaceType.ETHERNET: NetworkInterfaceType.ETHERNET,  # pyright: ignore[reportAttributeAccessIssue]
        InterfaceType.WLAN: NetworkInterfaceType.WLAN,  # pyright: ignore[reportAttributeAccessIssue]
        InterfaceType.BRIDGE: NetworkInterfaceType.BRIDGE,  # pyright: ignore[reportAttributeAccessIssue]
    },
    NetworkInterfaceState: {
        InterfaceOpState.NOT_PRESENT: NetworkInterfaceState.NOT_PRESENT,  # pyright: ignore[reportAttributeAccessIssue]
        InterfaceOpState.DOWN: NetworkInterfaceState.DOWN,  # pyright: ignore[reportAttributeAccessIssue]
        InterfaceOpState.NO_LINK: NetworkInterfaceState.NO_LINK,  # pyright: ignore[reportAttributeAccessIssue]
        InterfaceOpState.UP: NetworkInterfaceState.UP,  # pyright: ignore[reportAttributeAccessIssue]
    },
}
