"""Const for Raritan PX integration."""

from __future__ import annotations

from typing import Final
import datetime

from homeassistant.const import Platform

DOMAIN = "raritan_px"

DISCOVERY_TIMEOUT = 5  # Home Assistant will complain if startup takes > 10s
CONNECT_TIMEOUT = 5

DEFAULT_USERNAME: Final = "admin"
DEFAULT_PASSWORD: Final = "raritan"

CONF_CONFIG_ENTRY_MINOR_VERSION: Final = 1

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.SWITCH,
]

UPDATE_INTERVAL = datetime.timedelta(seconds=5)
