"""Raritan PDU API base models."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from raritan.rpc import Interface as RpcInterface

type RaritanUpdatableRpcMethodsList = list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[Any], None]]]


@dataclass(kw_only=True)
class RaritanUpdatable:
    """Representation of a generic updatable value."""

    def update_readings(self) -> RaritanUpdatableRpcMethodsList:
        """Return the API methods to update the sensor readings."""
        return []

    def update_info(self) -> RaritanUpdatableRpcMethodsList:
        """Return the API methods to update the sensor information."""
        return []
