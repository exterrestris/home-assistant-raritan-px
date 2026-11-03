"""Const for Raritan PX integration."""

from __future__ import annotations

import datetime as dt
from typing import Final

from homeassistant.const import Platform

DOMAIN = "raritan_px"

DISCOVERY_TIMEOUT = 5  # Home Assistant will complain if startup takes > 10s
CONNECT_TIMEOUT = 5

CONF_CONFIG_ENTRY_MINOR_VERSION: Final = 2

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.SWITCH,
]

DEFAULT_UPDATE_INTERVAL = dt.timedelta(seconds=5)
DISCOVERY_INTERVAL = dt.timedelta(minutes=15)
