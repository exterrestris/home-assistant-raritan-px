"""Raritan PDU API base models."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Flag, auto
from typing import Any

from raritan.rpc import Interface as RpcInterface

type RaritanUpdatableRpcMethodsList = list[tuple[tuple[RpcInterface.Method, list[Any]], Callable[[Any], None]]]


@dataclass(kw_only=True)
class RaritanModel:
    """Representation of a generic model."""


class RaritanUpdateOptions(Flag):
    """Flag to specify what sensor information to update."""

    NONE = 0
    METADATA = auto()
    VALUES = auto()
    ALL = METADATA | VALUES


@dataclass(kw_only=True)
class RaritanUpdatable:
    """Representation of a generic updatable value."""

    def update(self, options: RaritanUpdateOptions = RaritanUpdateOptions.ALL) -> RaritanUpdatableRpcMethodsList:
        """Return the API methods to update the requested information."""
        methods = []

        if options & RaritanUpdateOptions.METADATA:
            methods.extend(self._update_metadata())

        if options & RaritanUpdateOptions.VALUES:
            methods.extend(self._update_values())

        return methods

    def _update_metadata(self) -> RaritanUpdatableRpcMethodsList:
        return []

    def _update_values(self) -> RaritanUpdatableRpcMethodsList:
        return []
