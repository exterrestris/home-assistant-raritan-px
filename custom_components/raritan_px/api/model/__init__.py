from raritan.rpc import Interface as RpcInterface, Structure as RpcStructure

from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class RaritanUpdatable():
    """Representation of a generic updatable value."""

    source: RpcInterface

    def update_methods(self) -> list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[RpcStructure], None]]]:
        return []
