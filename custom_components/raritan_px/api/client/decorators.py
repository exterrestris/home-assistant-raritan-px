"""API client utility classes."""

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Final

from custom_components.raritan_px.api.client.errors import RaritanClientError
from custom_components.raritan_px.utils import seconds
from custom_components.raritan_px.utils.decorators import AsyncDecorator, ExtractLogger

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable


class Retry[**F, R](AsyncDecorator[F, R], ExtractLogger[F, R]):
    """Decorator to retry API client methods when exceptions are thrown."""

    DEFAULT_RETRIES: Final[int] = 5
    DEFAULT_WAIT: Final[timedelta] = timedelta(seconds=2)

    _catch: Iterable[type[Exception]]
    _max_retries: int
    _wait_for: float

    def __init__(
        self,
        *,
        max_retries: int = DEFAULT_RETRIES,
        retry_after: float | timedelta = DEFAULT_WAIT,
        catch: type[Exception] | Iterable[type[Exception]] = RaritanClientError,
    ) -> None:
        """Inititalise the decorator."""
        super().__init__(log_level=logging.INFO)

        self._max_retries = max_retries
        self._wait_for = seconds(retry_after)
        self._catch = [catch] if isinstance(catch, type) else catch

    async def _async_impl(self, func: Callable[F, Coroutine[None, None, R]], *args: F.args, **kwargs: F.kwargs) -> R:
        attempts = 0

        while True:
            try:
                result = await func(*args, **kwargs)
            except Exception as err:
                if not any(isinstance(err, err_type) for err_type in self._catch):
                    raise

                logger = self._get_logger()

                attempts += 1

                if attempts < self._max_retries:
                    if logger:
                        logger.debug(
                            "Retrying request %s in %.2f seconds after %s (attempt %s)",
                            func.__qualname__,
                            self._wait_for,
                            err.__class__.__name__,
                            attempts + 1,
                        )

                    await asyncio.sleep(self._wait_for)
                    continue

                if logger:
                    logger.info("Retry limit of %s reached for %s", self._max_retries, func.__qualname__)

                raise
            else:
                return result
