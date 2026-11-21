"""Decorators."""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from datetime import timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, cast, overload, override

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

# @todo Change to sentinel (requires Python 3.15+)
MISSING = object()


class BaseDecorator[**F, R](ABC):
    """Base class for reusable decorators."""

    @overload
    def __call__(
        self,
        func: Callable[F, Coroutine[None, None, R]],
    ) -> Callable[F, Coroutine[None, None, R]]: ...

    @overload
    def __call__(
        self,
        func: Callable[F, R],
    ) -> Callable[F, R]: ...

    def __call__(
        self,
        func: Callable[F, R] | Callable[F, Coroutine[None, None, R]],
    ) -> Callable[F, R] | Callable[F, Coroutine[None, None, R]]:
        """Call the decorator."""
        if inspect.iscoroutinefunction(func):
            async_func = cast("Callable[F, Coroutine[None, None, R]]", func)

            @wraps(func)
            async def async_wrapper(
                *args: F.args,
                **kwargs: F.kwargs,
            ) -> R:
                return await self._async_impl(async_func, *args, **kwargs)

            return async_wrapper

        sync_func = cast("Callable[F, R]", func)

        @wraps(func)
        def sync_wrapper(*args: F.args, **kwargs: F.kwargs) -> R:
            return self._sync_impl(sync_func, *args, **kwargs)

        return sync_wrapper

    @abstractmethod
    def _sync_impl(self, func: Callable[F, R], *args: Any, **kwargs: Any) -> R:
        """Handle sync functions."""
        raise NotImplementedError

    @abstractmethod
    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: Any, **kwargs: Any) -> R:
        """Handle async functions."""
        raise NotImplementedError


class SyncDecorator[**F, R](BaseDecorator[F, R]):
    """Base class for synchronous-only decorators."""

    @override
    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: Any, **kwargs: Any) -> R:
        msg = "Decorator does not support asynchronous functions."
        raise TypeError(msg)


class AsyncDecorator[**F, R](BaseDecorator[F, R]):
    """Base class for asynchronous-only decorators."""

    @override
    def _sync_impl(self, func: Callable[F, R], *args: Any, **kwargs: Any) -> R:
        msg = "Decorator does not support synchronous functions."
        raise TypeError(msg)


class SetProperty[**F, R](BaseDecorator[F, R]):
    """Decorator to set an instance property before/after executing a class method."""

    def __init__(
        self,
        prop: str,
        *,
        before: Any = MISSING,
        after: Any = MISSING,
    ) -> None:
        """Inititalise the decorator."""
        self._prop = prop
        self._before = before
        self._after = after

    def _set_before(self, instance: Any) -> None:
        if self._before != MISSING:
            setattr(instance, self._prop, self._before)

    def _set_after(self, instance: Any) -> None:
        if self._after != MISSING:
            setattr(instance, self._prop, self._after)

    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: Any, **kwargs: Any) -> R:
        self._set_before(args[0])
        result = await func(*args, **kwargs)
        self._set_after(args[0])
        return result

    def _sync_impl(self, func: Callable[F, R], *args: Any, **kwargs: Any) -> R:
        self._set_before(args[0])
        result = func(*args, **kwargs)
        self._set_after(args[0])
        return result


class Sleep[**F, R](AsyncDecorator[F, R]):
    """Decorator to pause/sleep before/after executing an async function."""

    def __init__(
        self,
        *,
        before: float | timedelta | None = None,
        after: float | timedelta | None = None,
    ) -> None:
        """Inititalise the decorator."""
        self._before = before
        self._after = after

    @staticmethod
    def _seconds(duration: float | timedelta | None) -> float:
        if duration is None:
            return 0

        return duration.total_seconds() if isinstance(duration, timedelta) else duration

    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: F.args, **kwargs: F.kwargs) -> R:
        if self._before is not None:
            await asyncio.sleep(self._seconds(self._before))

        result = await func(*args, **kwargs)

        if self._after is not None:
            await asyncio.sleep(self._seconds(self._after))

        return result
