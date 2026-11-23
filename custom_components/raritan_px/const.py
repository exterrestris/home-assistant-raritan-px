"""Const for Raritan PX integration."""

from __future__ import annotations

import datetime as dt
from typing import Final

from homeassistant.const import Platform

DOMAIN = "raritan_px"

DISCOVERY_TIMEOUT = 5  # Home Assistant will complain if startup takes > 10s
CONNECT_TIMEOUT = 5

CONF_CONFIG_ENTRY_MINOR_VERSION: Final = 4

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

DEFAULT_API_UPDATE_INTERVAL = dt.timedelta(seconds=5)
DEFAULT_FIRMWARE_UPDATE_INTERVAL = dt.timedelta(hours=12)
IN_PROGRESS_FIRMWARE_UPDATE_INTERVAL = dt.timedelta(seconds=2)
POST_FIRMWARE_UPDATE_INTERVAL = dt.timedelta(seconds=10)
DISCOVERY_INTERVAL = dt.timedelta(minutes=15)
POST_FIRMWARE_DOWNLOAD_DELAY = dt.timedelta(seconds=5)
POST_FIRMWARE_UPLOAD_DELAY = dt.timedelta(seconds=5)
POST_FIRMWARE_START_DELAY = dt.timedelta(seconds=5)
POST_FIRMWARE_UPDATE_DELAY = dt.timedelta(seconds=10)
POST_FIRMWARE_REFRESH_DELAY = dt.timedelta(seconds=5)

FIRMWARE_DOWNLOAD_PROGRESS_WEIGHT: Final[float] = 0.1
FIRMWARE_UPLOAD_PROGRESS_WEIGHT: Final[float] = 0.1
FIRMWARE_UPDATE_PROGRESS_WEIGHT: Final[float] = 0.75
