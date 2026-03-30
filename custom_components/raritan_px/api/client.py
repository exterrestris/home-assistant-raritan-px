"""API client for Raritan PX devices."""

from __future__ import annotations
from enum import Enum, Flag, auto
from itertools import product
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar
from raritan import rpc
from raritan.rpc import perform_bulk, Enumeration as RpcEnumeration
from raritan.rpc.pdumodel import Pdu, Outlet, Inlet, OverCurrentProtector
from raritan.rpc.cascading import CascadeManager
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import User, UserInfo
from homeassistant.core import HomeAssistant

from .model import RaritanUpdatable, RaritanUpdatableRpcMethodsList
from .model.device import RaritanPdu, RaritanPduDevice, RaritanPduInlet, RaritanPduOutlet
from .model.device.sensors import RaritanPduSensors
from .model.device.sensors import RaritanPduInletSensors
from .model.device.sensors import RaritanPduOutletSensors
from .model.device.states import RaritanState, OutletPowerState
from .model.sensor import RaritanSensor
from .const import API_TIMEOUT
from more_itertools import grouper, interleave, flatten

_LOGGER = logging.getLogger(__name__)

T = TypeVar('T', bound = "RaritanPduDevice", covariant = True)

STATE_API_ENUMERATION_PAIRS: dict[type[RaritanState], list[tuple[RaritanState, RpcEnumeration]]] = {
    OutletPowerState: [
        (OutletPowerState.ON, Outlet.PowerState.PS_ON), # pyright: ignore[reportAttributeAccessIssue]
        (OutletPowerState.OFF, Outlet.PowerState.PS_OFF), # pyright: ignore[reportAttributeAccessIssue]
    ],
}

API_TO_STATE_MAPPING: dict[type[RaritanState], dict[int, RaritanState]] = {
    state: { api_value.val: state for state, api_value in pairs} for state, pairs in STATE_API_ENUMERATION_PAIRS.items()
}

STATE_TO_API_MAPPING: dict[type[RaritanState], dict[RaritanState, RpcEnumeration]] = {
    state: { state: api_value for state, api_value in pairs} for state, pairs in STATE_API_ENUMERATION_PAIRS.items()
}


@dataclass
class ConnectionDetails:
    """Connection information for Raritan API."""

    host: str
    port: int = 443
    auth: AuthenticationDetails | None = None
    use_ssl: bool = False
    timeout: int = API_TIMEOUT


@dataclass
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

    def fetch_msg(self, sensor_count: int, device_count: int, requests_count: int) -> str:
        return "Fetching sensor {} for {} sensors for {} devices via {} requests".format(self.name.lower(), device_count, sensor_count, requests_count)

    def updated_msg(self, sensor_count: int) -> str:
        return "Updated sensor {} for {} sensors".format(self.name.lower(), sensor_count)

class UpdateSensors(Flag):
    NONE = 0
    INFO = auto()
    READINGS = auto()
    ALL = INFO | READINGS

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
            f"{self._config.host}:{self._config.port}",
            disable_certificate_verification = not self._config.use_ssl,
            timeout = self._config.timeout,
        )

    async def authenticate(self, *, force_reauth: bool = False) -> None:
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

                if force_reauth:
                    try:
                        _LOGGER.debug("Closing existing session and forcing re-authentication")

                        await self._hass.async_add_executor_job(
                            session_manager.closeCurrentSession,
                            SessionManager.CloseReason.CLOSE_REASON_FORCED_DISCONNECT, # pyright: ignore[reportAttributeAccessIssue]
                        )
                    except rpc.HttpException:
                        _LOGGER.debug("Failed to close existing session")
                    finally:
                        self._token = None
                else:
                    await self._hass.async_add_executor_job(
                        session_manager.touchCurrentSession, True # noqa: FBT003
                    )

                    _LOGGER.debug(
                        "Authenticated using session token for %s, session created at %s",
                        session_details.username,
                        session_details.creationTime,
                    )
            except rpc.HttpException:
                self._token = None

                _LOGGER.debug(
                    "Session has expired, will attempt to authenticate using credentials"
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

    async def close_session(self) -> None:
        """Close the current session and clear any stored session information."""

        if self._token is None:
            _LOGGER.debug("No active session to close")
            return

        session_manager = SessionManager("/session", self._agent)

        try:
            self._agent.set_auth_token(self._token)

            await self._hass.async_add_executor_job(
                session_manager.getCurrentSession
            )

            try:
                _LOGGER.debug("Closing session")

                await self._hass.async_add_executor_job(
                    session_manager.closeCurrentSession,
                    SessionManager.CloseReason.CLOSE_REASON_LOGOUT, # pyright: ignore[reportAttributeAccessIssue]
                )
            except rpc.HttpException:
                _LOGGER.debug("Failed to close session")

            else:
                await self._hass.async_add_executor_job(
                    session_manager.touchCurrentSession, True # noqa: FBT003
                )
        except rpc.HttpException:
            _LOGGER.debug("Session has expired")
        finally:
            self._token = None

    async def get_pdu_info(self, pdu_idx: int = 0, *, update_sensor_data: UpdateSensors = UpdateSensors.ALL) -> RaritanPdu:
        """Get information for the Raritan PDU."""
        await self.authenticate()

        try:
            pdu: Pdu = Pdu(f"/model/pdu/{pdu_idx}", self._agent)
            cascade = CascadeManager("/cascade", self._agent)

            responses = await self._hass.async_add_executor_job(
                perform_bulk, self._agent, [
                    (pdu.getMetaData, []),
                    (pdu.getSettings, []),
                    (pdu.getOutlets, []),
                    (pdu.getInlets, []),
                    (pdu.getSensors, []),
                    (cascade.getStatus, []),
                ]
            )

            pdu_metadata: Pdu.MetaData = responses[0] # pyright: ignore[reportAssignmentType]
            psu_settings: Pdu.Settings = responses[1] # pyright: ignore[reportAssignmentType]
            pdu_outlets: list[Outlet] = responses[2] # pyright: ignore[reportAssignmentType]
            pdu_inlets: list[Inlet] = responses[3] # pyright: ignore[reportAssignmentType]
            pdu_sensors: Pdu.Sensors = responses[4] # pyright: ignore[reportAssignmentType]
            status: CascadeManager.Status = responses[5] # pyright: ignore[reportAssignmentType]
        except rpc.HttpException as e:
            _LOGGER.exception(f"Error fetching PDU {pdu_idx} information")

            message: str = (
                f"Failed to fetch PDU {pdu_idx} information for {self._config.host}"
            )
            raise RaritanClientError(message) from e
        else:
            device = RaritanPdu(
                device_id = f"{pdu_metadata.nameplate.serialNumber}:/model/pdu/{pdu_idx}",
                pdu_id = pdu_idx,
                host = self._config.host,
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
            responses = await self._hass.async_add_executor_job(
                perform_bulk, self._agent, interleave(
                    [(outlet.getMetaData, []) for outlet in pdu_outlets],
                    [(outlet.getSettings, []) for outlet in pdu_outlets],
                    [(outlet.getSensors, []) for outlet in pdu_outlets],
                )
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
            _LOGGER.exception("Error fetching PDU outlets")

            message: str = f"Failed to fetch PDU outlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return outlets

    async def _get_inlets_info(self, pdu_inlets: list[Inlet], pdu_idx: int, pdu_serial: str) -> list[RaritanPduInlet]:
        try:
            responses = await self._hass.async_add_executor_job(
                perform_bulk, self._agent, interleave(
                    [(inlet.getMetaData, []) for inlet in pdu_inlets],
                    [(inlet.getSettings, []) for inlet in pdu_inlets],
                    [(inlet.getSensors, []) for inlet in pdu_inlets],
                )
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
            _LOGGER.exception("Error fetching PDU outlets")

            message: str = f"Failed to fetch PDU outlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return inlets

    async def _update_sensors_for_device(self, device: T, update_type: _SensorUpdate) -> T:
        update_requests = [
            (device, (device, sensor), request, update) for (device, sensor), (request, update) in list(
                flatten([
                    list(product([sensor], sensor_updates))
                    for sensor, sensor_updates in [
                        ((device_name, sensor_name), update_type.get_update_methods(sensor))
                        for (device_name, sensor_name, sensor) in [x for x in device.all_updatable_sensors]
                    ]
                ])
            )
        ]

        devices, sensors, requests, update_methods = [list(tup) for tup in zip(*update_requests)]

        _LOGGER.debug(update_type.fetch_msg(len(set(devices)), len(set(sensors)), len(requests)))

        responses = await self._hass.async_add_executor_job(
            perform_bulk, self._agent, interleave(requests)
        )

        for (_, response, method) in zip(sensors, responses, update_methods):
            method(response)

        _LOGGER.debug(update_type.updated_msg(len(set(sensors))))

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
        except rpc.HttpException as e:
            _LOGGER.exception(
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
    """Raised when a generic error occurs while communicating with the Raritan API."""


class AuthenticationError(RaritanClientError):
    """Raised when authentication with the Raritan API fails."""


class SessionCreationError(RaritanClientError):
    """Raised when creation of a new session with the Raritan API fails."""
