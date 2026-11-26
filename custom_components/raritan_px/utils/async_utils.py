"""Async utility classes/methods."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Coroutine


class CorountineWrapper[R](ABC):
    """Base class for reusable coroutine wrappers."""

    async def wrap(self, coro: Coroutine[None, None, R]) -> R:
        """Wrap and execute an existing coroutine object."""
        return await self._async_object_impl(coro)

    @abstractmethod
    async def _async_object_impl(self, coro: Coroutine[None, None, R]) -> R:
        raise NotImplementedError
