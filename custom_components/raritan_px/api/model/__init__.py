from raritan.rpc import Interface as RpcInterface

from dataclasses import dataclass
from typing import Any, Callable

type RaritanUpdatableRpcMethodsList = list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[Any], None]]]

@dataclass(kw_only=True)
class RaritanUpdatable():
    """Representation of a generic updatable value."""

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        return []

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        return []
