"""API client for Raritan PX devices."""

from __future__ import annotations
from enum import Enum, Flag, auto
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from ssl import SSLCertVerificationError
from typing import Iterable, TypeVar, Final
from time import monotonic
from raritan import rpc
from raritan.rpc import Time, Structure, perform_bulk
from raritan.rpc.pdumodel import Pdu, Outlet, Inlet, OverCurrentProtector
from raritan.rpc.cascading import CascadeManager
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import User, UserInfo
from homeassistant.core import HomeAssistant
from more_itertools import grouper, interleave

from custom_components.raritan_px.api.model import (
    RaritanUpdatable,
    RaritanUpdatableRpcMethodsList
)
from custom_components.raritan_px.api.model.device import (
    RaritanPdu,
    RaritanPduDevice,
    RaritanPduInlet,
    RaritanPduOutlet
)
from custom_components.raritan_px.api.model.device.sensors import (
    RaritanPduSensors,
    RaritanPduInletSensors,
    RaritanPduOutletSensors
)
from custom_components.raritan_px.api.model.device.states import OutletPowerState
from custom_components.raritan_px.api.const import API_TIMEOUT, DEFAULT_PORT
from custom_components.raritan_px.api.mappings import STATE_TO_API_MAPPING

_LOGGER = logging.getLogger(__name__)

T = TypeVar('T', bound = "RaritanPduDevice", covariant = True)

@dataclass(frozen=True)
class ConnectionDetails:
    """Connection information for Raritan API."""

    host: str
    auth: AuthenticationDetails | None = None
    port: int = DEFAULT_PORT
    use_ssl: bool = True
    verify_ssl: bool = True
    timeout: int = API_TIMEOUT


@dataclass(frozen=True)
class AuthenticationDetails:
    """Authentication information for Raritan API."""

    user: str
    passwd: str


@dataclass(frozen=True)
class _SensorUpdateMethod:
    method: Callable[[RaritanUpdatable], RaritanUpdatableRpcMethodsList]


class _SensorUpdate(Enum):
    INFO = _SensorUpdateMethod(lambda sensor: sensor.update_info())
    READINGS = _SensorUpdateMethod(lambda sensor: sensor.update_readings())

    def get_update_methods(self, sensor: RaritanUpdatable) -> RaritanUpdatableRpcMethodsList:
        return self.value.method(sensor)

    def fetch_msg(self, sensor_count: int, device_count: int) -> str:
        return "sensor {} for {} sensors across {} devices".format(self.name.lower(), device_count, sensor_count)

class UpdateSensors(Flag):
    NONE = 0
    INFO = auto()
    READINGS = auto()
    ALL = INFO | READINGS

class RaritanClient:
    """Client for Raritan API."""

    _agent: rpc.Agent
    _hass: HomeAssistant
    _config: ConnectionDetails
    _session_manager: SessionManager
    _session_token: str | None = None
    _session_created: datetime | None = None
    _logger: logging.Logger = _LOGGER

    def __init__(self, hass: HomeAssistant, config: ConnectionDetails, logger: logging.Logger | None = None) -> None:
        """Init Raritan client."""

        if not config.host:
            raise ConfigError("No host provider")

        self._hass = hass
        self._config = config
        self._agent = rpc.Agent(
            self._get_protocol(),
            f"{self._config.host}:{self._config.port}",
            disable_certificate_verification = not self._config.verify_ssl,
            timeout = self._config.timeout,
        )
        self._session_manager = SessionManager("/session", self._agent)

        if logger is not None:
            self._logger = logger

    def _get_protocol(self) -> str:
        HTTPS: Final = "https"
        HTTP: Final = "http"

        if self._config.use_ssl:
            return HTTPS

        return HTTP

    def _extract_original_exception(self, e: rpc.HttpException):
        try:
            previous = e.args[1]
        except IndexError:
            return
        else:
            if not isinstance(e.args[1], Exception):
                return

        raise previous

    async def authenticate(self, *, force_reauth: bool = False) -> None:
        """Authenticate with the Raritan API, using either an existing session token or username/password."""
        if self._config.auth is None:
            message: str = (
                f"No authentication information provided for {self._config.host}"
            )
            raise AuthenticationError(message)

        if self._session_token is not None:
            try:
                self._agent.set_auth_token(self._session_token)

                session_details: Session = await self._hass.async_add_executor_job(
                    self._session_manager.getCurrentSession
                )

                if session_details.username != self._config.auth.user:
                    force_reauth = True

                    self._logger.warning(
                        "User %s attempting to use session token for user %s to authenticate with %s",
                        self._config.auth.user,
                        session_details.username,
                        self._config.host
                    )

                if force_reauth:
                    try:
                        self._logger.info("Closing existing session and forcing re-authentication")

                        await self._close_session(
                            session_details,
                            SessionManager.CloseReason.CLOSE_REASON_FORCED_DISCONNECT, # pyright: ignore[reportAttributeAccessIssue]
                        )
                    except SessionCloseError as e:
                        # This has already been logged
                        pass
                    finally:
                        self._clear_session_data()
                else:
                    await self._hass.async_add_executor_job(
                        self._session_manager.touchCurrentSession, True # noqa: FBT003
                    )

                    self._logger.debug(
                        "Authenticated using session token for %s, session created at %s",
                        session_details.username,
                        self._session_created
                    )
            except rpc.HttpException:
                self._clear_session_data()

                self._logger.debug(
                    "Session has expired, will attempt to authenticate using credentials"
                )

        if self._session_token is None:
            try:
                response: int

                self._agent.set_auth_basic(
                    self._config.auth.user, self._config.auth.passwd
                )

                user = User("/auth/currentUser", self._agent)
                user_info: UserInfo = await self._hass.async_add_executor_job(
                    user.getInfo
                )

                self._logger.info(
                    "Authenticated with %s as %s (%s)",
                    self._config.host,
                    self._config.auth.user,
                    user_info.auxInfo.fullname,
                )

                session_details: Session

                (
                    response,
                    session_details,
                    self._session_token,
                ) = await self._hass.async_add_executor_job(self._session_manager.newSession)

                if response == SessionManager.ERR_ACTIVE_SESSION_EXCLUSIVE_FOR_USER:
                    message: str = (
                        f"Failed to create new session for logged-in user {self._config.auth.user}"
                    )
                    raise ConcurrentLoginError(message)

                # The Raritan JSON-RPC API returns the session created time as a timestamp in microseconds relative to
                # system boot, however the Raritan Python SDK creates a datetime instance from that value as if it were
                # a POSIX timestamp. To get an accurate creation time, we need to undo this

                session_creation: Time = session_details.creationTime # pyright: ignore[reportAssignmentType]
                self._session_created = datetime.now() - timedelta(microseconds=session_creation.timestamp())

                self._logger.debug("Session created for %s at %s", session_details.username, self._session_created)
            except rpc.HttpException as e:
                try:
                    self._extract_original_exception(e)
                except SSLCertVerificationError as e:
                    raise CertificateVerificationError() from e
                else:
                    self._logger.exception("Authentication Error")

                    message: str = f"Failed to authenticate as {self._config.auth.user}"
                    raise AuthenticationError(message) from e

    def _clear_session_data(self) -> None:
        self._session_token = None
        self._session_created = None

    async def _close_session(self, session_details: Session, reason: SessionManager.CloseReason) -> bool:
        try:
            self._agent.set_auth_token(self._session_token)

            self._logger.debug("Closing session for %s created at %s", session_details.username, self._session_created)

            await self._hass.async_add_executor_job(self._session_manager.closeCurrentSession, reason)
        except rpc.HttpException as e:
            self._logger.warning("Failed to close existing session for %s", session_details.username, exc_info=True)

            raise SessionCloseError
        else:
            self._logger.info("Session closed for %s", session_details.username)
        finally:
            self._clear_session_data()

        return True

    async def close_session(self) -> bool:
        """Close the current session and clear any stored session information."""

        if self._session_token is None:
            self._logger.debug("No active session to close")
            return False

        try:
            self._agent.set_auth_token(self._session_token)

            session_details: Session = await self._hass.async_add_executor_job(
                self._session_manager.getCurrentSession
            )

            return await self._close_session(
                session_details,
                SessionManager.CloseReason.CLOSE_REASON_LOGOUT # pyright: ignore[reportAttributeAccessIssue]
            )
        except rpc.HttpException:
            self._logger.debug("Session expired before close request")
        finally:
            self._clear_session_data()

        return True

    async def _execute_bulk_requests(self, requests: Iterable, data_name: str | None = None) -> list[Structure]:
        try:
            if log_timing := self._logger.isEnabledFor(logging.DEBUG):
                start = monotonic()

            responses = await self._hass.async_add_executor_job(
                perform_bulk, self._agent, requests
            )

            return responses # pyright: ignore[reportReturnType]
        finally:
            if log_timing:
                self._logger.debug(
                    "%s %s requests in %.3f seconds",
                    f"Fetched {data_name} via" if data_name else "Fetched",
                    len(responses),
                    monotonic() - start,
                )

    async def get_pdu_info(self, pdu_idx: int = 0, *, update_sensor_data: UpdateSensors = UpdateSensors.ALL) -> RaritanPdu:
        """Get information for the Raritan PDU."""
        await self.authenticate()

        try:
            pdu: Pdu = Pdu(f"/model/pdu/{pdu_idx}", self._agent)
            cascade = CascadeManager("/cascade", self._agent)

            responses = await self._execute_bulk_requests(
                [
                    (pdu.getMetaData, []),
                    (pdu.getSettings, []),
                    (pdu.getOutlets, []),
                    (pdu.getInlets, []),
                    (pdu.getSensors, []),
                    (cascade.getStatus, []),
                ],
                f"PDU {pdu_idx} information",
            )

            pdu_metadata: Pdu.MetaData = responses[0] # pyright: ignore[reportAssignmentType]
            psu_settings: Pdu.Settings = responses[1] # pyright: ignore[reportAssignmentType]
            pdu_outlets: list[Outlet] = responses[2] # pyright: ignore[reportAssignmentType]
            pdu_inlets: list[Inlet] = responses[3] # pyright: ignore[reportAssignmentType]
            pdu_sensors: Pdu.Sensors = responses[4] # pyright: ignore[reportAssignmentType]
            status: CascadeManager.Status = responses[5] # pyright: ignore[reportAssignmentType]
        except rpc.HttpException as e:
            self._logger.exception(f"Error fetching PDU {pdu_idx} information")

            message: str = (
                f"Failed to fetch PDU {pdu_idx} information for {self._config.host}"
            )
            raise RaritanClientError(message) from e
        else:
            device = RaritanPdu(
                device_id = f"{pdu_metadata.nameplate.serialNumber}:/model/pdu/{pdu_idx}",
                pdu_id = pdu_idx,
                host = self._config.host,
                url = f"{self._get_protocol()}://{self._config.host}/",
                name = psu_settings.name,
                manufacturer = pdu_metadata.nameplate.manufacturer,
                model = pdu_metadata.nameplate.model,
                serial_number = pdu_metadata.nameplate.serialNumber,
                firmware_version = pdu_metadata.fwRevision,
                hardware_version = pdu_metadata.hwRevision,
                mac_address = pdu_metadata.macAddress,
                has_switchable_outlets = pdu_metadata.hasSwitchableOutlets,
                has_metered_outlets = pdu_metadata.hasMeteredOutlets,
                is_standalone = status.role == CascadeManager.Role.STANDALONE, # pyright: ignore[reportAttributeAccessIssue]
                outlets = await self._get_outlets_info(pdu_outlets, pdu_idx, pdu_metadata.nameplate.serialNumber),
                inlets = await self._get_inlets_info(pdu_inlets, pdu_idx, pdu_metadata.nameplate.serialNumber),
                sensors = RaritanPduSensors.from_sensor_sources({
                    'power_supply_status': pdu_sensors.powerSupplyStatus,
                    'active_power': pdu_sensors.activePower,
                    'apparent_power': pdu_sensors.apparentPower,
                    'active_energy': pdu_sensors.activeEnergy,
                    'apparent_energy': pdu_sensors.apparentEnergy,
                })
            )

            if update_sensor_data | UpdateSensors.INFO:
                return await self._update_sensor_info_for_device(device)

            if update_sensor_data | UpdateSensors.READINGS:
                return await self._update_sensor_readings_for_device(device)

            return device

    async def _get_outlets_info(self, pdu_outlets: list[Outlet], pdu_idx: int, pdu_serial: str) -> list[RaritanPduOutlet]:
        try:
            responses = await self._execute_bulk_requests(
                interleave(
                    [(outlet.getMetaData, []) for outlet in pdu_outlets],
                    [(outlet.getSettings, []) for outlet in pdu_outlets],
                    [(outlet.getSensors, []) for outlet in pdu_outlets],
                ),
                f"outlet data for PDU {pdu_idx}",
            )

            outlets: list[RaritanPduOutlet] = []

            outlet_metadata: Outlet.MetaData
            outlet_settings: Outlet.Settings
            outlet_sensors: Outlet.Sensors

            for outlet_idx, (outlet_metadata, outlet_settings, outlet_sensors) in enumerate(grouper(responses, 3)): # pyright: ignore[reportAssignmentType]
                outlets.append(
                    RaritanPduOutlet(
                        device_id = f"{pdu_serial}:/model/pdu/{pdu_idx}/outlet/{outlet_idx}",
                        pdu_id = pdu_idx,
                        outlet_id = outlet_idx,
                        name = outlet_settings.name,
                        label = outlet_metadata.label,
                        is_switchable = outlet_metadata.isSwitchable,
                        sensors = RaritanPduOutletSensors.from_sensor_sources({
                            'voltage': outlet_sensors.voltage,
                            'current': outlet_sensors.current,
                            'peak_current': outlet_sensors.peakCurrent,
                            'maximum_current': outlet_sensors.maximumCurrent,
                            'unbalanced_current': outlet_sensors.unbalancedCurrent,
                            'active_power': outlet_sensors.activePower,
                            'reactive_power': outlet_sensors.reactivePower,
                            'apparent_power': outlet_sensors.apparentPower,
                            'power_factor': outlet_sensors.powerFactor,
                            'displacement_power_factor': outlet_sensors.displacementPowerFactor,
                            'active_energy': outlet_sensors.activeEnergy,
                            'phase_angle': outlet_sensors.phaseAngle,
                            'line_frequency': outlet_sensors.lineFrequency,
                            'crest_factor': outlet_sensors.crestFactor,
                            'voltage_total_harmonic_distortion': outlet_sensors.voltageThd,
                            'current_total_harmonic_distortion': outlet_sensors.currentThd,
                            'inrush_current': outlet_sensors.inrushCurrent,
                            'outlet_state': outlet_sensors.outletState,
                        }),
                    )
                )
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU outlets")

            message: str = f"Failed to fetch PDU outlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return outlets

    async def _get_inlets_info(self, pdu_inlets: list[Inlet], pdu_idx: int, pdu_serial: str) -> list[RaritanPduInlet]:
        try:
            responses = await self._execute_bulk_requests(
                interleave(
                    [(inlet.getMetaData, []) for inlet in pdu_inlets],
                    [(inlet.getSettings, []) for inlet in pdu_inlets],
                    [(inlet.getSensors, []) for inlet in pdu_inlets],
                ),
                f"inlet data for PDU {pdu_idx}",
            )

            inlets: list[RaritanPduInlet] = []

            inlet_metadata: Inlet.MetaData
            inlet_settings: Inlet.Settings
            inlet_sensors: Inlet.Sensors

            for inlet_idx, (inlet_metadata, inlet_settings, inlet_sensors) in enumerate(grouper(responses, 3)): # pyright: ignore[reportAssignmentType]
                inlets.append(
                    RaritanPduInlet(
                        device_id = f"{pdu_serial}:/model/pdu/{pdu_idx}/inlet/{inlet_idx}",
                        pdu_id = pdu_idx,
                        inlet_id = inlet_idx,
                        name = inlet_settings.name,
                        label = inlet_metadata.label,
                        sensors = RaritanPduInletSensors.from_sensor_sources({
                            'voltage': inlet_sensors.voltage,
                            'current': inlet_sensors.current,
                            'peak_current': inlet_sensors.peakCurrent,
                            'residual_current': inlet_sensors.residualCurrent,
                            'residual_ac_current': inlet_sensors.residualACCurrent,
                            'residual_dc_current': inlet_sensors.residualDCCurrent,
                            'active_power': inlet_sensors.activePower,
                            'reactive_power': inlet_sensors.reactivePower,
                            'apparent_power': inlet_sensors.apparentPower,
                            'power_factor': inlet_sensors.powerFactor,
                            'displacement_power_factor': inlet_sensors.displacementPowerFactor,
                            'active_energy': inlet_sensors.activeEnergy,
                            'apparent_energy': inlet_sensors.apparentEnergy,
                            'unbalanced_current': inlet_sensors.unbalancedCurrent,
                            'unbalanced_line_line_current': inlet_sensors.unbalancedLineLineCurrent,
                            'unbalanced_voltage': inlet_sensors.unbalancedVoltage,
                            'unbalanced_line_line_voltage': inlet_sensors.unbalancedLineLineVoltage,
                            'line_frequency': inlet_sensors.lineFrequency,
                            'phase_angle': inlet_sensors.phaseAngle,
                            'crest_factor': inlet_sensors.crestFactor,
                            'voltage_total_harmonic_distortion': inlet_sensors.voltageThd,
                            'current_total_harmonic_distortion': inlet_sensors.currentThd,
                            'power_quality': inlet_sensors.powerQuality,
                            'surge_protector_status': inlet_sensors.surgeProtectorStatus,
                            'residual_current_status': inlet_sensors.residualCurrentStatus,
                        }),
                    )
                )
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU inlets")

            message: str = f"Failed to fetch PDU inlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return inlets

    async def _update_sensors_for_device(self, device: T, update_type: _SensorUpdate) -> T:
        update_requests = [
            (device_name, (device_name, sensor_name), request, update)
            for (device_name, sensor_name, sensor) in device.all_updatable_sensors
            for (request, update) in update_type.get_update_methods(sensor)
        ]

        devices, sensors, requests, update_methods = [list(tup) for tup in zip(*update_requests)]

        responses = await self._execute_bulk_requests(
            interleave(requests),
            update_type.fetch_msg(len(set(devices)), len(set(sensors)))
        )

        for (response, method) in zip(responses, update_methods):
            method(response)

        return device

    async def _update_sensor_info_for_device(self, device: T) -> T:
        return await self._update_sensors_for_device(device, _SensorUpdate.INFO)

    async def _update_sensor_readings_for_device(self, device: T) -> T:
        return await self._update_sensors_for_device(device, _SensorUpdate.READINGS)

    async def update_sensor_readings_for_pdu(self, pdu: RaritanPdu) -> RaritanPdu:
        await self.authenticate()

        return await self._update_sensor_readings_for_device(pdu)

    async def set_outlet_power_state(
        self,
        pdu_idx: int = 0,
        outlet_idx: int = 0,
        state: OutletPowerState = OutletPowerState.ON
    ) -> OutletPowerState:
        """Get the power state for a specific Raritan PDU outlet."""
        await self.authenticate()

        try:
            outlet = Outlet(f"/model/pdu/{pdu_idx}/outlet/{outlet_idx}", self._agent)

            status: int = await self._hass.async_add_executor_job(
                outlet.setPowerState, STATE_TO_API_MAPPING[OutletPowerState][state]
            )

            self._logger.debug(f"Changed PDU {pdu_idx} outlet {outlet_idx} state to {state.name}")
        except rpc.HttpException as e:
            self._logger.exception(
                "Error setting PDU {pdu_idx} outlet {outlet_idx} power state"
            )

            message: str = f"Failed to set PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            match status:
                case 0: #OK
                    return state
                case Outlet.ERR_OUTLET_NOT_SWITCHABLE:
                    message = f"Outlet not switchable for PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"
                case Outlet.ERR_OUTLET_DISABLED:
                    message = f"Outlet disabled for PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"
                case Outlet.ERR_RELAY_CONTROL_DISABLED:
                    message = f"Outlet relay control disabled for PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"
                case _:
                    message = f"Unexpected response setting PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"

            raise RaritanClientError(message)


class RaritanClientError(Exception):
    """Base exception for all client exceptions"""


class ConfigError(RaritanClientError):
    """Raised when configuration is invalid."""


class CommunicationError(Exception):
    """Raised when a generic error occurs while communicating with the Raritan API."""


class CertificateVerificationError(CommunicationError):
    """Raised when SSL certificate verification fails"""


class AuthenticationError(CommunicationError):
    """Raised when authentication fails."""


class SessionError(CommunicationError):
    """Raised when session operations fail."""


class ConcurrentLoginError(AuthenticationError, SessionError):
    """Raised when creation of a new session fails due single login limitation."""


class SessionCloseError(SessionError):
    """Raised when closing the current session."""
