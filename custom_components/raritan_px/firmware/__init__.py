"""Firmware management."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePath
from shutil import rmtree
from typing import TYPE_CHECKING, Any
from zipfile import ZipFile, ZipInfo

from aiohttp import ClientError, ClientResponse
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
from custom_components.raritan_px.utils.decorators import LogExecutionTime

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.storage import Store


_LOGGER = logging.getLogger(__name__)

type DownloadProgress = Callable[[int, int], None]


class FirmwareManager:
    """Firmware manager."""

    _hass: HomeAssistant
    _store: Store
    _session: ClientSession | None = None
    _logger: logging.Logger = _LOGGER
    _tmp_dir: Path
    _github_api_rate_limit: int | None = None
    _github_api_rate_limit_remaining: int | None = None
    _github_api_wait_until: datetime | None = None

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

        try:
            if catalogue and not force_update:
                if not update_check:
                    return catalogue

                self._logger.debug("Checking for firmware catalogue update")

                (latest, _) = await self._get_latest_version()

                if not catalogue.is_out_of_date(latest):
                    return catalogue

            catalogue = await self._download_latest_catalogue()

            await self._save_catalogue_to_store(catalogue)
        except GitHubApiRateLimitExceededError:
            if not catalogue:
                raise

            self._logger.warning("Unable to update firmware catalogue from GitHub due to rate limiting")

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

    def is_rate_limited(self) -> bool:
        """Check if requests to the GitHub API are rate limited."""
        return self._github_api_wait_until is not None

    def _check_rate_limit(self) -> None:
        if self._github_api_wait_until is None:
            return

        if datetime.now(UTC) > self._github_api_wait_until + timedelta(seconds=10):
            self._github_api_wait_until = None
            return

        raise GitHubApiRateLimitExceededError(self._github_api_rate_limit, self._github_api_wait_until)

    def _update_rate_limit(self, response: ClientResponse) -> None:
        rate_limit = response.headers.getone("X-RateLimit-Limit", None)
        remaining = response.headers.getone("X-RateLimit-Remaining", None)
        reset_timestamp = response.headers.getone("X-RateLimit-Reset", None)
        retry_after = response.headers.getone("Retry-After", None)

        match response.status:
            case 403, 429:
                if retry_after:
                    self._github_api_wait_until = datetime.now(UTC) + timedelta(seconds=int(retry_after))
                elif reset_timestamp:
                    self._github_api_wait_until = datetime.fromtimestamp(int(reset_timestamp), UTC)
                else:
                    self._github_api_wait_until = datetime.now(UTC) + timedelta(minutes=10)

                raise GitHubApiRateLimitExceededError(
                    int(rate_limit) if rate_limit else None,
                    self._github_api_wait_until,
                )
            case _:
                self._github_api_wait_until = None

                if rate_limit:
                    self._github_api_rate_limit = int(rate_limit)

                if remaining:
                    self._github_api_rate_limit_remaining = int(remaining)

    async def _get_latest_version(self) -> tuple[str, dict]:
        self._check_rate_limit()

        session = self._get_session()

        try:
            async with session.get(CATALOGUE_URL) as response:
                self._update_rate_limit(response)

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

    @LogExecutionTime(
        "Downloaded latest firmware catalogue", log_level=logging.INFO, log_when=LogExecutionTime.ON_SUCCESS
    )
    async def _download_latest_catalogue(self) -> FirmwareCatalogue:
        self._check_rate_limit()

        session = self._get_session()

        self._logger.debug("Downloading latest firmware catalogue")

        url = await self._get_latest_url()

        try:
            async with session.get(url, headers={"Accept": "application/octet-stream"}) as response:
                self._update_rate_limit(response)

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

    async def download_firmware(
        self, firmware: Firmware, *, callback: DownloadProgress | None = None
    ) -> tuple[Path, int]:
        """Download the specified firmware and return the path to the file."""
        fw_zip = await self._download_firmware(firmware, callback)
        return await self._extract_firmware(fw_zip, self._get_tmp_dir(firmware))

    def _get_path(self, firmware: Firmware) -> PurePath:
        if firmware.firmware_url.path is None:
            raise ValueError

        return PurePath(firmware.firmware_url.path)

    def _get_tmp_dir(self, firmware: Firmware) -> Path:
        return self._tmp_dir / self._get_path(firmware).stem

    def _get_tmp_zip(self, firmware: Firmware) -> Path:
        return self._get_tmp_dir(firmware) / self._get_path(firmware).name

    @LogExecutionTime(
        lambda _, firmware, *_s: f"Downloaded firmware zip from {firmware.firmware_url!s}",
        log_level=logging.INFO,
        log_when=LogExecutionTime.ON_SUCCESS,
    )
    async def _download_firmware(self, firmware: Firmware, callback: DownloadProgress | None) -> Path:
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
            async with session.get(str(firmware.firmware_url), raise_for_status=True) as response:
                total_bytes = int(response.headers.get("Content-Length", 0))
                downloaded = 0

                with await self._hass.async_add_executor_job(file.open, "wb") as fd:
                    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK):
                        await self._hass.async_add_executor_job(fd.write, chunk)

                        if total_bytes and callback:
                            downloaded += len(chunk)
                            callback(downloaded, total_bytes)
                return file
        except ClientError as err:
            raise FirmwareArchiveDownloadError from err

    async def _extract_firmware(self, fw_zip: Path, extract_to: Path) -> tuple[Path, int]:
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

        def _process_zip() -> tuple[Path, int]:
            with ZipFile(fw_zip) as zip_file:
                fw_info = _validate_zip(zip_file)
                fw_bin = extract_to / fw_info.filename

                zip_file.extract(fw_info, fw_bin)

                self._logger.info("Extracted %s from firmware zip", fw_bin.name)

                return (fw_bin, fw_info.file_size)

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


class GitHubApiRateLimitExceededError(FirmwareCatalogueError):
    """Raised when requests to the GitHub API are being rate limited."""

    limit: int | None
    reset: datetime | None

    def __init__(self, limit: int | None, reset: datetime | None) -> None:
        """Init the exception."""
        super().__init__()
        self.limit = limit
        self.reset = reset

    def __reduce__(self) -> str | tuple[Any, ...]:
        """Allow pickling the exception."""
        return (GitHubApiRateLimitExceededError, (self.limit, self.reset))


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
