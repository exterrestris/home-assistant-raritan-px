"""Firmware catalogue management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pydantic import ValidationError

from custom_components.raritan_px.firmware.const import CATALOGUE_FILE, CATALOGUE_STORE, CATALOGUE_URL
from custom_components.raritan_px.firmware.model import FirmwareCatalogue

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.storage import Store


_LOGGER = logging.getLogger(__name__)


class FirmwareCatalogueManager:
    """Firmware catalogue manager."""

    _hass: HomeAssistant
    _store: Store
    _session: ClientSession | None = None
    _logger: logging.Logger = _LOGGER

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger | None = None,
    ) -> None:
        """Init catalogue manager."""
        self._hass = hass
        self._store = hass.data[CATALOGUE_STORE]

        if logger is not None:
            self._logger = logger

    async def get_catalogue(self, *, update_check: bool = False, force_update: bool = False) -> FirmwareCatalogue:
        """Get the firmware catalogue."""
        catalogue = await self._get_catalogue_from_store()

        if catalogue and not force_update:
            if not update_check:
                return catalogue

            (latest, _) = await self._get_latest_version()

            if not catalogue.is_out_of_date(latest):
                return catalogue

        catalogue = await self._download_latest_catalogue()

        await self._save_catalogue_to_store(catalogue)

        return catalogue

    async def _get_catalogue_from_store(self) -> FirmwareCatalogue | None:
        try:
            data = await self._store.async_load()

            if data is not None:
                catalogue = FirmwareCatalogue.model_validate(data)

                self._logger.debug("Loaded firmware catalogue data from HA store")

                return catalogue
        except ValidationError:
            self._logger.warning("Unable to parse saved firmware catalogue data")

        return None

    async def _save_catalogue_to_store(self, catalogue: FirmwareCatalogue) -> None:
        data = catalogue.model_dump(mode="json")

        self._logger.debug("Saving firmware catalogue data to HA store")

        await self._store.async_save(data)

    def _get_session(self) -> ClientSession:
        if self._session is None:
            self._session = async_get_clientsession(self._hass)

        return self._session

    async def _get_latest_version(self) -> tuple[str, dict]:
        session = self._get_session()

        try:
            async with session.get(CATALOGUE_URL) as response:
                release = await response.json()

                return (release.get("tag_name"), release)
        except Exception as err:
            raise CommunicationError from err

    async def _get_latest_url(self) -> str:
        (_, release) = await self._get_latest_version()

        for asset in release.get("assets", []):  # pyright: ignore[reportOptionalIterable]
            if asset.get("name") == CATALOGUE_FILE:
                return asset.get("url")

        raise ReleaseParseError

    async def _download_latest_catalogue(self) -> FirmwareCatalogue:
        session = self._get_session()

        self._logger.info("Downloading latest firmware catalogue")

        url = await self._get_latest_url()

        async with session.get(url, headers={"Accept": "application/octet-stream"}) as response:
            json = await response.text()

            return self._parse_catalogue(json)

    def _parse_catalogue(self, json: str) -> FirmwareCatalogue:
        try:
            return FirmwareCatalogue.model_validate_json(json)
        except ValidationError as err:
            self._logger.exception("Unable to parse downlaoded catalogue data")

            raise CatalogueParseError from err


class FirmwareCatalogueManagerError(Exception):
    """Base exception for all client exceptions."""


class ReleaseParseError(FirmwareCatalogueManagerError):
    """Raised when GitHub release data cannot be parsed."""


class CatalogueParseError(FirmwareCatalogueManagerError):
    """Raised when catalogue cannot be parsed."""


class CommunicationError(FirmwareCatalogueManagerError):
    """Raised when a generic error occurs while communicating with the Raritan API."""
