"""Utility functions."""

from datetime import timedelta
from itertools import (
    chain,
    zip_longest,
)
from typing import TYPE_CHECKING, Any

from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterable


def seconds(duration: float | timedelta) -> float:
    """Convert a duration to a number of seconds."""
    return duration.total_seconds() if isinstance(duration, timedelta) else duration


def normalise_version(version: str | Version, *, segments: int = 3) -> Version:
    """Strip build information from version string."""
    if isinstance(version, Version):
        return version

    v = Version(version)
    v = (*v.release, *(((0),) * 3))[:segments]
    return Version(".".join(map(str, v)))


# Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes
def flatten(list_of_lists: Iterable[Iterable]) -> chain:
    """Return an iterator flattening one level of nesting in a list of lists."""
    return chain.from_iterable(list_of_lists)


# Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes
def interleave(*iterables: Iterable) -> chain:
    """Return a new iterable yielding from each iterable in turn, until the shortest is exhausted."""
    return chain.from_iterable(zip(*iterables, strict=False))


# Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes
def grouper(iterable: Iterable, n: int, fillvalue: Any = None) -> zip_longest:
    """Group elements from *iterable* into fixed-length groups of length *n*."""
    iterators = [iter(iterable)] * n
    return zip_longest(*iterators, fillvalue=fillvalue)
