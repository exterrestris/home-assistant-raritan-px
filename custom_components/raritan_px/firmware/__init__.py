"""Firmware management."""

from __future__ import annotations

import logging
from pathlib import Path, PurePath
from shutil import rmtree
from typing import TYPE_CHECKING
from zipfile import ZipFile, ZipInfo

from aiohttp import ClientError
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from custom_components.raritan_px.const import DOMAIN
from custom_components.raritan_px.firmware.const import (
    CATALOGUE_FILE,
    CATALOGUE_STORE,
    CATALOGUE_URL,
    DOWNLOAD_CHUNK,
    FIRMWARE_DIR,
    FIRMWARE_SUFFIX,
    FIRMWARE_ZIP_MAX_FILES,
    FIRMWARE_ZIP_MAX_SIZE,
)
from custom_components.raritan_px.firmware.model import Firmware, FirmwareCatalogue

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.storage import Store


_LOGGER = logging.getLogger(__name__)


class FirmwareManager:
    """Firmware manager."""

    _hass: HomeAssistant
    _store: Store
    _session: ClientSession | None = None
    _logger: logging.Logger = _LOGGER
    _tmp_dir: Path

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger | None = None,
    ) -> None:
        """Init firmware manager."""
        self._hass = hass
        self._store = hass.data[CATALOGUE_STORE]
        self._tmp_dir = Path(hass.config.cache_path(DOMAIN, FIRMWARE_DIR))

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
            self._logger.warning("Unable to parse saved firmware catalogue data", exc_info=True)
        except HomeAssistantError:
            self._logger.warning("Unable to load saved firmware catalogue data", exc_info=True)

        return None

    async def _save_catalogue_to_store(self, catalogue: FirmwareCatalogue) -> None:
        try:
            self._logger.debug("Saving firmware catalogue data to HA store")
            data = catalogue.model_dump(mode="json")

            await self._store.async_save(data)
        except HomeAssistantError, PydanticSerializationError:
            self._logger.exception("Unable to save firmware catalogue data")

    def _get_session(self) -> ClientSession:
        if self._session is None:
            self._session = async_get_clientsession(self._hass)

        return self._session

    async def _get_latest_version(self) -> tuple[str, dict]:
        session = self._get_session()

        try:
            async with session.get(CATALOGUE_URL) as response:
                release = await response.json()

                if release.get("tag_name"):
                    return (release.get("tag_name"), release)
        except ClientError as err:
            raise GitHubApiHttpError from err
        except Exception as err:
            raise GitHubApiParseError from err

        raise GitHubApiParseError

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

        try:
            async with session.get(url, headers={"Accept": "application/octet-stream"}) as response:
                json = await response.text()

                return self._parse_catalogue(json)
        except ClientError as err:
            raise GitHubApiHttpError from err

    def _parse_catalogue(self, json: str) -> FirmwareCatalogue:
        try:
            return FirmwareCatalogue.model_validate_json(json)
        except ValidationError as err:
            self._logger.exception("Unable to parse downlaoded catalogue data")

            raise CatalogueParseError from err

    async def download_firmware(self, firmware: Firmware) -> Path:
        """Download the specified firmware and return the path to the file."""
        fw_zip = await self._download_firmware(firmware)
        return await self._extract_firmware(fw_zip, self._get_tmp_dir(firmware))

    def _get_path(self, firmware: Firmware) -> PurePath:
        if firmware.firmware_url.path is None:
            raise ValueError

        return PurePath(firmware.firmware_url.path)

    def _get_tmp_dir(self, firmware: Firmware) -> Path:
        return self._tmp_dir / self._get_path(firmware).stem

    def _get_tmp_zip(self, firmware: Firmware) -> Path:
        return self._get_tmp_dir(firmware) / self._get_path(firmware).name

    async def _download_firmware(self, firmware: Firmware) -> Path:
        def _create_dir(path: Path) -> None:
            if path.exists():
                # Clear any existing file/directory
                rmtree(path)

            path.mkdir(parents=True, exist_ok=True)

        session = self._get_session()
        tmp_dir = self._get_tmp_dir(firmware)
        file = self._get_tmp_zip(firmware)

        await self._hass.async_add_executor_job(_create_dir, tmp_dir)

        try:
            async with session.get(str(firmware.firmware_url)) as response:
                with await self._hass.async_add_executor_job(file.open, "wb") as fd:
                    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK):
                        await self._hass.async_add_executor_job(fd.write, chunk)

                self._logger.info("Downloaded firmware zip from %s", str(firmware.firmware_url))
                return file
        except ClientError as err:
            raise FirmwareArchiveDownloadError from err

    async def _extract_firmware(self, fw_zip: Path, extract_to: Path) -> Path:
        def _validate_zip(zip_file: ZipFile) -> ZipInfo:
            # Validate zip contents to protect against zip bombs (see: https://github.com/python/cpython/issues/80643)
            # and check for presence of one and only one firmware binary
            total_size = 0
            fw_bin_info = None

            for file_count, info in enumerate(zip_file.infolist(), start=1):
                total_size += info.file_size

                if file_count > FIRMWARE_ZIP_MAX_FILES:
                    msg = f"Zip contains too many files (>{FIRMWARE_ZIP_MAX_FILES}), possible zip bomb"
                    raise ValueError(msg)

                if total_size > FIRMWARE_ZIP_MAX_SIZE:
                    msg = f"Zip uncompressed size too large (>{FIRMWARE_ZIP_MAX_SIZE} bytes), possible zip bomb"
                    raise ValueError(msg)

                if PurePath(info.filename).suffix == FIRMWARE_SUFFIX:
                    if fw_bin_info:
                        msg = "Multiple binaries found in firmware zip"
                        raise ValueError(msg)

                    fw_bin_info = info

            if fw_bin_info:
                return fw_bin_info

            msg = "No firmware binary found in firmware zip"
            raise ValueError(msg)

        def _process_zip() -> Path:
            with ZipFile(fw_zip) as zip_file:
                fw_info = _validate_zip(zip_file)
                fw_bin = extract_to / fw_info.filename

                zip_file.extract(fw_info, fw_bin)

                self._logger.debug("Extracted %s from firmware zip", fw_bin.name)

                return fw_bin

        try:
            return await self._hass.async_add_executor_job(_process_zip)
        except Exception as err:
            raise ExtractFirmwareError from err


class FirmwareManagerError(Exception):
    """Base exception for all exceptions."""


class FirmwareCatalogueError(FirmwareManagerError):
    """Base exception for all catalogue exceptions."""


class ParseError(FirmwareCatalogueError):
    """Generic parsing exception."""


class ReleaseParseError(ParseError):
    """Raised when GitHub release data cannot be parsed."""


class CatalogueParseError(ParseError):
    """Raised when catalogue cannot be parsed."""


class HttpClientError(FirmwareManagerError):
    """Raised when a generic error occurs handling an HTTP request."""


class GitHubApiError(FirmwareCatalogueError):
    """Raised when a generic error occurs communicating with or handling response data from the GitHub API."""


class GitHubApiParseError(GitHubApiError, ParseError):
    """Raised when a generic error occurs communicating with or handling response data from the GitHub API."""


class GitHubApiHttpError(HttpClientError, GitHubApiError):
    """Raised when a generic error occurs handling an HTTP request to the GitHub API."""


class FirmwareDownloadError(FirmwareManagerError):
    """Base exception for all firmware download exceptions."""


class FirmwareArchiveDownloadError(HttpClientError, FirmwareDownloadError):
    """Raised when a generic error occurs handling a firmware download over HTTP."""


class ExtractFirmwareError(FirmwareDownloadError):
    """Raised when a generic error occurs extracting a firmware binary from a firmware download."""
