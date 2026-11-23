"""Decorators."""

from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum, auto
from functools import wraps
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast, overload, override

from custom_components.raritan_px.utils import CorountineWrapper

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

# @todo Change to sentinel (requires Python 3.15+)
MISSING = object()

_LOGGER = logging.getLogger(__name__)


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


class LogExecutionTime[**F, R](AsyncDecorator[F, R], CorountineWrapper[R]):
    """Log function execution time when DEBUG logging is enabled."""

    class _When(Enum):
        ALWAYS = auto()
        ON_SUCCESS = auto()

    ALWAYS = _When.ALWAYS
    ON_SUCCESS = _When.ON_SUCCESS

    def __init__(
        self,
        message: str | Callable[..., str] | None = None,
        *,
        logger: logging.Logger | None = None,
        log_level: int = logging.DEBUG,
        log_when: _When = ALWAYS,
    ) -> None:
        """Initialise the decorator."""
        self._message = message
        self._logger = logger
        self._log_level = log_level
        self._when = log_when

    def _get_logger(self, args: tuple[object, ...] | None = None) -> logging.Logger | None:
        logger = _LOGGER

        if self._logger:
            logger = self._logger
        elif args:
            instance_logger = getattr(args[0], "_logger", None)

            if isinstance(instance_logger, logging.Logger):
                logger = instance_logger

        return logger if logger.isEnabledFor(logging.DEBUG) else None

    def _build_message(self, func: Callable[..., Any], args: tuple[object, ...], kwargs: dict[str, Any]) -> str:
        if self._message is None:
            return f"{func.__qualname__} executed"

        if isinstance(self._message, str):
            return self._message

        return self._message(*args, **kwargs)

    def _log_execution_time(self, logger: logging.Logger, msg: str, elapsed: float) -> None:
        logger.log(self._log_level, "%s in %.6f seconds", msg, elapsed)

    def _sync_impl(self, func: Callable[F, R], *args: F.args, **kwargs: F.kwargs) -> R:
        if not (logger := self._get_logger(args)):
            return func(*args, **kwargs)

        start = perf_counter()

        try:
            success = True
            return func(*args, **kwargs)
        except:
            success = False
            raise
        finally:
            if self._when == self.ALWAYS or success:
                msg = self._build_message(cast("Callable[..., object]", func), args, kwargs)
                self._log_execution_time(logger, msg, perf_counter() - start)

    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: F.args, **kwargs: F.kwargs) -> R:
        if not (logger := self._get_logger(args)):
            return await func(*args, **kwargs)

        start = perf_counter()

        try:
            success = True
            return await func(*args, **kwargs)
        except:
            success = False
            raise
        finally:
            if self._when == self.ALWAYS or success:
                msg = self._build_message(cast("Callable[..., object]", func), args, kwargs)
                self._log_execution_time(logger, msg, perf_counter() - start)

    async def _async_object_impl(self, coro: Coroutine[None, None, R]) -> R:
        if not (logger := self._get_logger()):
            return await coro

        start = perf_counter()

        try:
            success = True
            return await coro
        except:
            success = False
            raise
        finally:
            if self._when == self.ALWAYS or success:
                msg = self._message if isinstance(self._message, str) else "Coroutine executed"
                self._log_execution_time(logger, msg, perf_counter() - start)
