"""API client for Raritan PX devices."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from raritan import rpc
from raritan.rpc import pdumodel
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import User, UserInfo
from homeassistant.core import HomeAssistant
from .const import API_TIMEOUT
_LOGGER = logging.getLogger(__name__)


@dataclass
class ConnectionDetails:
    """Connection information for Raritan API."""

    host: str
    auth: AuthenticationDetails | None = None
    use_ssl: bool = False
    timeout: int = API_TIMEOUT


@dataclass
class AuthenticationDetails:
    """Authentication information for Raritan API."""

    user: str
    passwd: str


class AuthenticationError(Exception):
    """Raised when authentication with the Raritan API fails."""


class SessionCreationError(Exception):
    """Raised when creation of a new session with the Raritan API fails."""


class RaritanClientError(Exception):
    """Raised when a generic error occurs while communicating with the Raritan API."""


class RaritanClient:
    """Client for Raritan API."""

    PROTOCOL = "https"

    def __init__(self, hass: HomeAssistant, config: ConnectionDetails) -> None:
        """Init Raritan client."""
        self._hass: HomeAssistant = hass
        self._config: ConnectionDetails = config
        self._token: str | None = None
        self._agent: rpc.Agent = rpc.Agent(
            self.PROTOCOL,
            self._config.host,
            disable_certificate_verification=not self._config.use_ssl,
            timeout=self._config.timeout,
        )

    async def authenticate(self) -> None:
        """Authenticate with the Raritan API, using either an existing session token or username/password."""
        if self._config.auth is None:
            message: str = (
                f"No authentication information provided for {self._config.host}"
            )
            raise AuthenticationError(message)

        session_manager = SessionManager("/session", self._agent)
        session_details: Session

        if self._token is not None:
            try:
                self._agent.set_auth_token(self._token)

                session_details = await self._hass.async_add_executor_job(
                    session_manager.getCurrentSession
                )

                _LOGGER.debug(
                    "Authenticated using session token for %s, session created at %s",
                    session_details.username,
                    session_details.creationTime,
                )
            except rpc.HttpException as e:
                self._token = None

                _LOGGER.debug(
                    "Session token is invalid, will attempt to authenticate using credentials"
                )

        if self._token is None:
            try:
                success: int

                self._agent.set_auth_basic(
                    self._config.auth.user, self._config.auth.passwd
                )

                user = User("/auth/currentUser", self._agent)
                user_info: UserInfo = await self._hass.async_add_executor_job(
                    user.getInfo
                )

                _LOGGER.debug(
                    "Authenticated as %s (%s)",
                    self._config.auth.user,
                    user_info.auxInfo.fullname,
                )

                (
                    success,
                    session_details,
                    self._token,
                ) = await self._hass.async_add_executor_job(session_manager.newSession)

                if success == 1:
                    message: str = (
                        f"Failed to create session for user {self._config.auth.user}"
                    )
                    raise SessionCreationError(message)
            except rpc.HttpException as e:
                _LOGGER.exception("Authentication Error")

                message: str = f"Failed to authenticate as {self._config.auth.user}"
                raise AuthenticationError(message) from e

    async def get_pdu_info(self, pdu_idx: int = 0) -> RaritanPdu:
        """Get information for the Raritan PDU."""
        await self.authenticate()

        try:
            pdu = pdumodel.Pdu(f"/model/pdu/{pdu_idx}", self._agent)
            metadata: pdumodel.Pdu.MetaData = await self._hass.async_add_executor_job(
                pdu.getMetaData
            )
            settings: pdumodel.Pdu.Settings = await self._hass.async_add_executor_job(
                pdu.getSettings
            )

            return RaritanPdu(
                host=self._config.host,
                name=settings.name,
                model=metadata.nameplate.model,
                serial_number=metadata.nameplate.serialNumber,
                firmware_version=metadata.fwRevision,
                mac_address=metadata.macAddress,
                has_switchable_outlets=metadata.hasSwitchableOutlets,
                has_metered_outlets=metadata.hasMeteredOutlets,
            )
        except rpc.HttpException as e:
            _LOGGER.exception("Error fetching PDU metadata")

            message: str = f"Failed to fetch PDU metadata for {self._config.host}"
            raise RaritanClientError(message) from e


@dataclass
class RaritanPdu:
    """Representation of a Raritan PDU device."""

    host: str
    name: str
    model: str
    serial_number: str
    firmware_version: str
    mac_address: str
    has_switchable_outlets: bool
    has_metered_outlets: bool
