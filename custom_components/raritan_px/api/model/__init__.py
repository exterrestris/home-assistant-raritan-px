from raritan.rpc import Interface as RpcInterface

from dataclasses import dataclass
from typing import Any, Callable

type RaritanUpdatableRpcMethodsList = list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[Any], None]]]

@dataclass
class RaritanUpdatable():
    """Representation of a generic updatable value."""

    source: RpcInterface

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return []

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        return []
