"""Utility functions."""

from datetime import timedelta

from packaging.version import Version


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
