"""Utility classes/methods."""

from abc import ABC, abstractmethod
from asyncio import Lock
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:
    from collections.abc import Coroutine


class CorountineWrapper[R](ABC):
    """Base class for reusable decorators."""

    async def wrap(self, coro: Coroutine[None, None, R]) -> R:
        """Wrap and execute an existing coroutine object."""
        return await self._async_object_impl(coro)

    @abstractmethod
    async def _async_object_impl(self, coro: Coroutine[None, None, R]) -> R:
        raise NotImplementedError


class Manager[T](ABC):
    """Generic manager class."""

    _items: dict[str, T]

    def __init__(self) -> None:
        """Initialise the manager."""
        self._items = {}

    @abstractmethod
    def _create(self, name: str) -> T:
        raise NotImplementedError

    def get(self, name: str, *args: Any, **kwargs: Any) -> T:
        """Get a managed item by name, creating it if it doeesn't exist."""
        if name not in self._items:
            self._items[name] = self._create(name, *args, **kwargs)

        return self._items[name]

    def create(self, name: str, *args: Any, **kwargs: Any) -> T:
        """Create a managed item by name and store for later retreival."""
        if name in self._items:
            raise KeyError

        self._items[name] = self._create(name, *args, **kwargs)

        return self._items[name]


class LockManager(Manager[Lock]):
    """Lock manager class."""

    @override
    def _create(self, name: str) -> Lock:
        return Lock()


def seconds(duration: float | timedelta) -> float:
    """Convert a duration to a number of seconds."""
    return duration.total_seconds() if isinstance(duration, timedelta) else duration
