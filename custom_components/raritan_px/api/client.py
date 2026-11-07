"""API client for Raritan PX devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum, Flag, auto
from ssl import SSLCertVerificationError
from time import monotonic
from typing import TYPE_CHECKING, Final, TypeVar

from more_itertools import flatten, grouper, interleave
from raritan import rpc
from raritan.rpc import Structure, Time, perform_bulk
from raritan.rpc.cascading import CascadeManager
from raritan.rpc.net import Info, InterfaceInfo, Net
from raritan.rpc.pdumodel import Inlet, Outlet, OverCurrentProtector, Pdu
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import User, UserInfo

from custom_components.raritan_px.api.const import API_TIMEOUT, DEFAULT_PORT
from custom_components.raritan_px.api.mappings import STATE_TO_API_MAPPING
from custom_components.raritan_px.api.model.device.pdu import RaritanPdu, RaritanPduSensors
from custom_components.raritan_px.api.model.device.pdu.inlet import (
    RaritanPduInlet,
    RaritanPduInletSensors,
)
from custom_components.raritan_px.api.model.device.pdu.ocp import (
    RaritanPduOverCurrentProtector,
    RaritanPduOverCurrentProtectorSensors,
)
from custom_components.raritan_px.api.model.device.pdu.outlet import (
    RaritanPduOutlet,
    RaritanPduOutletSensors,
)
from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState
from custom_components.raritan_px.api.model.network import (
    NETWORK_ENUM_TYPE_VALUE_MAPPING,
    NetworkInterface,
    NetworkInterfaceState,
    NetworkInterfaceType,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from homeassistant.core import HomeAssistant

    from custom_components.raritan_px.api.model import (
        RaritanUpdatable,
        RaritanUpdatableRpcMethodsList,
    )
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.sensor import RaritanSensor

RaritanDevice_co = TypeVar("RaritanDevice_co", bound="RaritanDevice", covariant=True)

_LOGGER = logging.getLogger(__name__)


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

    def fetch_msg(self, device: RaritanDevice, device_count: int, sensor_count: int) -> Callable[[], str]:
        return lambda: (
            f"sensor {self.name.lower()} from {device.device_id} for {sensor_count} sensors across {device_count} devices"  # noqa: E501
        )


class PduDevices(Flag):
    """Flag to specify what sensor information to update."""

    NONE = 0
    INLETS = auto()
    OUTLETS = auto()
    OCPS = auto()
    ALL = INLETS | OUTLETS | OCPS


class UpdateSensors(Flag):
    """Flag to specify what sensor information to update."""

    NONE = 0
    INFO = auto()
    READINGS = auto()
    ALL = INFO | READINGS


class RaritanClient:
    """Client for Raritan API."""

    _HTTPS: Final = "https"
    _HTTP: Final = "http"

    _agent: rpc.Agent
    _hass: HomeAssistant
    _config: ConnectionDetails
    _session_manager: SessionManager
    _session_token: str | None = None
    _session_created: datetime | None = None
    _logger: logging.Logger = _LOGGER

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConnectionDetails,
        logger: logging.Logger | None = None,
    ) -> None:
        """Init Raritan client."""
        if not config.host:
            msg = "No host provider"
            raise ConfigError(msg)

        self._hass = hass
        self._config = config
        self._agent = rpc.Agent(
            self._get_protocol(),
            f"{self._config.host}:{self._config.port}",
            disable_certificate_verification=not self._config.verify_ssl,
            timeout=self._config.timeout,
        )
        self._session_manager = SessionManager("/session", self._agent)

        if logger is not None:
            self._logger = logger

    def _get_protocol(self) -> str:
        if self._config.use_ssl:
            return self._HTTPS

        return self._HTTP

    def _extract_original_exception(self, e: rpc.HttpException) -> None:
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
        if self._session_token is not None:
            await self._authenticate_with_token(force_reauth=force_reauth)

        if self._session_token is None:
            await self._authenticate_with_credentials()

    async def _authenticate_with_token(self, *, force_reauth: bool = False) -> None:
        if self._config.auth is None:
            message: str = f"No authentication information provided for {self._config.host}"
            raise AuthenticationError(message)

        try:
            self._agent.set_auth_token(self._session_token)

            session_details: Session = await self._hass.async_add_executor_job(self._session_manager.getCurrentSession)

            if session_details.username != self._config.auth.user:
                force_reauth = True

                self._logger.warning(
                    "User %s attempting to use session token for user %s to authenticate with %s",
                    self._config.auth.user,
                    session_details.username,
                    self._config.host,
                )

            if force_reauth:
                try:
                    self._logger.info(
                        "Closing existing session on %s and forcing re-authentication",
                        self._config.host,
                    )

                    await self._close_session(
                        session_details,
                        SessionManager.CloseReason.CLOSE_REASON_FORCED_DISCONNECT,  # pyright: ignore[reportAttributeAccessIssue]
                    )
                except SessionCloseError:
                    # This has already been logged
                    pass
                finally:
                    self._clear_session_data()
            else:
                await self._hass.async_add_executor_job(
                    self._session_manager.touchCurrentSession,
                    True,  # noqa: FBT003
                )

                self._logger.debug(
                    "Authenticated with %s using session token for %s, session created at %s",
                    self._config.host,
                    session_details.username,
                    self._session_created,
                )
        except rpc.HttpException:
            self._clear_session_data()

            self._logger.debug(
                "Session token for %s has expired, will attempt to authenticate using credentials",
                self._config.host,
            )

    async def _authenticate_with_credentials(self) -> None:
        if self._config.auth is None:
            message: str = f"No authentication information provided for {self._config.host}"
            raise AuthenticationError(message)

        try:
            response: int

            self._agent.set_auth_basic(self._config.auth.user, self._config.auth.passwd)

            user = User("/auth/currentUser", self._agent)
            user_info: UserInfo = await self._hass.async_add_executor_job(user.getInfo)

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
                    f"Failed to create new session on {self._config.host} for logged-in user {self._config.auth.user}"
                )
                raise ConcurrentLoginError(message)

            # The Raritan JSON-RPC API returns the session created time as a timestamp in microseconds relative to
            # system boot, however the Raritan Python SDK creates a datetime instance from that value as if it were
            # a POSIX timestamp. To get an accurate creation time, we need to undo this

            session_creation: Time = session_details.creationTime  # pyright: ignore[reportAssignmentType]
            self._session_created = datetime.now(UTC) - timedelta(microseconds=session_creation.timestamp())

            self._logger.debug(
                "Session created for %s on %s at %s",
                session_details.username,
                self._config.host,
                self._session_created,
            )
        except rpc.HttpException as e:
            try:
                self._extract_original_exception(e)
            except SSLCertVerificationError as e:
                raise CertificateVerificationError from e
            else:
                self._logger.exception("Authentication Error")

                message: str = f"Failed to authenticate as {self._config.auth.user} on {self._config.host}"
                raise AuthenticationError(message) from e

    def _clear_session_data(self) -> None:
        self._session_token = None
        self._session_created = None

    async def _close_session(self, session_details: Session, reason: SessionManager.CloseReason) -> bool:
        try:
            self._agent.set_auth_token(self._session_token)

            self._logger.debug(
                "Closing session for %s on %s created at %s",
                session_details.username,
                self._config.host,
                self._session_created,
            )

            await self._hass.async_add_executor_job(self._session_manager.closeCurrentSession, reason)
        except rpc.HttpException as err:
            self._logger.warning(
                "Failed to close existing session for %s on %s",
                session_details.username,
                self._config.host,
                exc_info=True,
            )

            raise SessionCloseError from err
        else:
            self._logger.info(
                "Session closed for %s on %s",
                session_details.username,
                self._config.host,
            )
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

            session_details: Session = await self._hass.async_add_executor_job(self._session_manager.getCurrentSession)

            return await self._close_session(
                session_details,
                SessionManager.CloseReason.CLOSE_REASON_LOGOUT,  # pyright: ignore[reportAttributeAccessIssue]
            )
        except rpc.HttpException:
            self._logger.debug("Session expired before close request")
        finally:
            self._clear_session_data()

        return True

    async def _execute_bulk_requests(
        self, requests: Iterable, data_name: str | Callable[[], str] | None = None
    ) -> list[Structure]:
        if log_timing := self._logger.isEnabledFor(logging.DEBUG):
            start = monotonic()

        responses = await self._hass.async_add_executor_job(perform_bulk, self._agent, requests)

        if log_timing:
            if callable(data_name):
                data_name = data_name()

            self._logger.debug(
                "Fetched %s %s requests in %.3f seconds",
                f"{data_name} via" if data_name else "",
                len(responses),
                monotonic() - start,
            )

        return responses  # pyright: ignore[reportReturnType]

    async def get_pdu_info(
        self,
        pdu_idx: int = 0,
        *,
        populate: PduDevices = PduDevices.ALL,
        update: UpdateSensors = UpdateSensors.ALL,
    ) -> RaritanPdu:
        """Get information for the Raritan PDU."""
        await self.authenticate()

        try:
            pdu: Pdu = Pdu(f"/model/pdu/{pdu_idx}", self._agent)
            cascade = CascadeManager("/cascade", self._agent)
            net = Net("/net", self._agent)

            responses = await self._execute_bulk_requests(
                [
                    (pdu.getMetaData, []),
                    (pdu.getSettings, []),
                    (pdu.getOutlets, []),
                    (pdu.getInlets, []),
                    (pdu.getOverCurrentProtectors, []),
                    (pdu.getSensors, []),
                    (cascade.getStatus, []),
                    (net.getInfo, []),
                ],
                f"PDU {pdu_idx} information",
            )

            pdu_metadata: Pdu.MetaData = responses[0]  # pyright: ignore[reportAssignmentType]
            psu_settings: Pdu.Settings = responses[1]  # pyright: ignore[reportAssignmentType]
            pdu_outlets: list[Outlet] = responses[2]  # pyright: ignore[reportAssignmentType]
            pdu_inlets: list[Inlet] = responses[3]  # pyright: ignore[reportAssignmentType]
            pdu_ocps: list[OverCurrentProtector] = responses[4]  # pyright: ignore[reportAssignmentType]
            pdu_sensors: Pdu.Sensors = responses[5]  # pyright: ignore[reportAssignmentType]
            status: CascadeManager.Status = responses[6]  # pyright: ignore[reportAssignmentType]
            net_info: Info = responses[7]  # pyright: ignore[reportAssignmentType]
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU %s information", pdu_idx)

            message: str = f"Failed to fetch PDU {pdu_idx} information for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            interfaces: dict[str, InterfaceInfo] = net_info.ifMap
            network_interfaces: dict[str, NetworkInterface] = {
                key: NetworkInterface(
                    name=interface.name,
                    label=interface.label,
                    type=NETWORK_ENUM_TYPE_VALUE_MAPPING[NetworkInterfaceType][interface.type],  # pyright: ignore[reportArgumentType]
                    enabled=interface.enabled,
                    state=NETWORK_ENUM_TYPE_VALUE_MAPPING[NetworkInterfaceState][interface.state],  # pyright: ignore[reportArgumentType],
                    mac_address=interface.macAddr,
                )
                for key, interface in interfaces.items()
            }

            device = RaritanPdu(
                device_id=f"{pdu_metadata.nameplate.serialNumber}:/model/pdu/{pdu_idx}",
                rid=pdu.target,
                id=pdu_idx,
                host=self._config.host,
                url=f"{self._get_protocol()}://{self._config.host}/",
                name=psu_settings.name,
                manufacturer=pdu_metadata.nameplate.manufacturer,
                model=pdu_metadata.nameplate.model,
                serial_number=pdu_metadata.nameplate.serialNumber,
                firmware_version=pdu_metadata.fwRevision,
                hardware_version=pdu_metadata.hwRevision,
                mac_address=pdu_metadata.macAddress,
                has_switchable_outlets=pdu_metadata.hasSwitchableOutlets,
                has_metered_outlets=pdu_metadata.hasMeteredOutlets,
                is_standalone=status.role == CascadeManager.Role.STANDALONE,  # pyright: ignore[reportAttributeAccessIssue]
                voltage_rating=pdu_metadata.nameplate.rating.voltage,
                current_rating=pdu_metadata.nameplate.rating.current,
                frequency_rating=pdu_metadata.nameplate.rating.frequency,
                power_rating=pdu_metadata.nameplate.rating.power,
                sensors=RaritanPduSensors.from_sensor_sources(
                    {
                        "power_supply_status": pdu_sensors.powerSupplyStatus,
                        "active_power": pdu_sensors.activePower,
                        "apparent_power": pdu_sensors.apparentPower,
                        "active_energy": pdu_sensors.activeEnergy,
                        "apparent_energy": pdu_sensors.apparentEnergy,
                    }
                ),
                network_interfaces=network_interfaces,
            )

            if populate | PduDevices.OUTLETS:
                await self._get_outlets_info(pdu_outlets, device, pdu_metadata.nameplate.serialNumber)

            if populate | PduDevices.INLETS:
                await self._get_inlets_info(pdu_inlets, device, pdu_metadata.nameplate.serialNumber)

            if populate | PduDevices.OCPS:
                await self._get_ocps_info(pdu_ocps, device, pdu_metadata.nameplate.serialNumber)

            if update | UpdateSensors.INFO:
                return await self._update_all_sensor_info_for_device(device)

            if update | UpdateSensors.READINGS:
                return await self.update_all_sensor_readings_for_device(device)

            return device

    async def _get_outlets_info(
        self, pdu_outlets: list[Outlet], pdu: RaritanPdu, pdu_serial: str
    ) -> list[RaritanPduOutlet]:
        try:
            responses = await self._execute_bulk_requests(
                interleave(
                    [(outlet.getMetaData, []) for outlet in pdu_outlets],
                    [(outlet.getSettings, []) for outlet in pdu_outlets],
                    [(outlet.getSensors, []) for outlet in pdu_outlets],
                    [(outlet.getIOP, []) for outlet in pdu_outlets],
                ),
                f"outlet data for PDU {pdu.id}",
            )

            outlets: list[RaritanPduOutlet] = []

            outlet_metadata: Outlet.MetaData
            outlet_settings: Outlet.Settings
            outlet_sensors: Outlet.Sensors
            inlet: Inlet
            ocp: OverCurrentProtector

            for outlet_idx, (
                outlet_metadata,
                outlet_settings,
                outlet_sensors,
                (inlet, ocp, _),
            ) in enumerate(grouper(responses, 4)):  # pyright: ignore[reportGeneralTypeIssues, reportAssignmentType]
                outlet = RaritanPduOutlet(
                    device_id=f"{pdu_serial}:/model/pdu/{pdu.id}/outlet/{outlet_idx}",
                    rid=pdu_outlets[outlet_idx].target,
                    inlet_rid=inlet.target,
                    ocp_rid=ocp.target,
                    id=outlet_idx,
                    name=outlet_settings.name,
                    label=outlet_metadata.label,
                    receptacle_type=outlet_metadata.receptacleType,
                    is_switchable=outlet_metadata.isSwitchable,
                    sensors=RaritanPduOutletSensors.from_sensor_sources(
                        {
                            "voltage": outlet_sensors.voltage,
                            "current": outlet_sensors.current,
                            "peak_current": outlet_sensors.peakCurrent,
                            "maximum_current": outlet_sensors.maximumCurrent,
                            "unbalanced_current": outlet_sensors.unbalancedCurrent,
                            "active_power": outlet_sensors.activePower,
                            "reactive_power": outlet_sensors.reactivePower,
                            "apparent_power": outlet_sensors.apparentPower,
                            "power_factor": outlet_sensors.powerFactor,
                            "displacement_power_factor": outlet_sensors.displacementPowerFactor,
                            "active_energy": outlet_sensors.activeEnergy,
                            "phase_angle": outlet_sensors.phaseAngle,
                            "line_frequency": outlet_sensors.lineFrequency,
                            "crest_factor": outlet_sensors.crestFactor,
                            "voltage_total_harmonic_distortion": outlet_sensors.voltageThd,
                            "current_total_harmonic_distortion": outlet_sensors.currentThd,
                            "inrush_current": outlet_sensors.inrushCurrent,
                            "outlet_state": outlet_sensors.outletState,
                        }
                    ),
                )

                outlets.append(pdu.add_outlet(outlet))
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU outlets")

            message: str = f"Failed to fetch PDU outlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return outlets

    async def _get_inlets_info(
        self, pdu_inlets: list[Inlet], pdu: RaritanPdu, pdu_serial: str
    ) -> list[RaritanPduInlet]:
        try:
            responses = await self._execute_bulk_requests(
                interleave(
                    [(inlet.getMetaData, []) for inlet in pdu_inlets],
                    [(inlet.getSettings, []) for inlet in pdu_inlets],
                    [(inlet.getSensors, []) for inlet in pdu_inlets],
                ),
                f"inlet data for PDU {pdu.id}",
            )

            inlets: list[RaritanPduInlet] = []

            inlet_metadata: Inlet.MetaData
            inlet_settings: Inlet.Settings
            inlet_sensors: Inlet.Sensors

            for inlet_idx, (inlet_metadata, inlet_settings, inlet_sensors) in enumerate(grouper(responses, 3)):  # pyright: ignore[reportAssignmentType]
                inlet = RaritanPduInlet(
                    device_id=f"{pdu_serial}:/model/pdu/{pdu.id}/inlet/{inlet_idx}",
                    rid=pdu_inlets[inlet_idx].target,
                    id=inlet_idx,
                    name=inlet_settings.name,
                    label=inlet_metadata.label,
                    plug_type=inlet_metadata.plugType,
                    sensors=RaritanPduInletSensors.from_sensor_sources(
                        {
                            "voltage": inlet_sensors.voltage,
                            "current": inlet_sensors.current,
                            "peak_current": inlet_sensors.peakCurrent,
                            "residual_current": inlet_sensors.residualCurrent,
                            "residual_ac_current": inlet_sensors.residualACCurrent,
                            "residual_dc_current": inlet_sensors.residualDCCurrent,
                            "active_power": inlet_sensors.activePower,
                            "reactive_power": inlet_sensors.reactivePower,
                            "apparent_power": inlet_sensors.apparentPower,
                            "power_factor": inlet_sensors.powerFactor,
                            "displacement_power_factor": inlet_sensors.displacementPowerFactor,
                            "active_energy": inlet_sensors.activeEnergy,
                            "apparent_energy": inlet_sensors.apparentEnergy,
                            "unbalanced_current": inlet_sensors.unbalancedCurrent,
                            "unbalanced_line_line_current": inlet_sensors.unbalancedLineLineCurrent,
                            "unbalanced_voltage": inlet_sensors.unbalancedVoltage,
                            "unbalanced_line_line_voltage": inlet_sensors.unbalancedLineLineVoltage,
                            "line_frequency": inlet_sensors.lineFrequency,
                            "phase_angle": inlet_sensors.phaseAngle,
                            "crest_factor": inlet_sensors.crestFactor,
                            "voltage_total_harmonic_distortion": inlet_sensors.voltageThd,
                            "current_total_harmonic_distortion": inlet_sensors.currentThd,
                            "power_quality": inlet_sensors.powerQuality,
                            "surge_protector_status": inlet_sensors.surgeProtectorStatus,
                            "residual_current_status": inlet_sensors.residualCurrentStatus,
                        }
                    ),
                )

                inlets.append(pdu.add_inlet(inlet))
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU inlets")

            message: str = f"Failed to fetch PDU inlets for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return inlets

    async def _get_ocps_info(
        self, pdu_ocps: list[OverCurrentProtector], pdu: RaritanPdu, pdu_serial: str
    ) -> list[RaritanPduOverCurrentProtector]:
        try:
            responses = await self._execute_bulk_requests(
                interleave(
                    [(ocp.getMetaData, []) for ocp in pdu_ocps],
                    [(ocp.getSettings, []) for ocp in pdu_ocps],
                    [(ocp.getSensors, []) for ocp in pdu_ocps],
                    [(ocp.getInlet, []) for ocp in pdu_ocps],
                ),
                f"ocp data for PDU {pdu.id}",
            )

            ocps: list[RaritanPduOverCurrentProtector] = []

            ocp_metadata: OverCurrentProtector.MetaData
            ocp_settings: OverCurrentProtector.Settings
            ocp_sensors: OverCurrentProtector.Sensors
            inlet: Inlet

            for ocp_idx, (ocp_metadata, ocp_settings, ocp_sensors, inlet) in enumerate(grouper(responses, 4)):  # pyright: ignore[reportAssignmentType]
                ocp = RaritanPduOverCurrentProtector(
                    device_id=f"{pdu_serial}:/model/pdu/{pdu.id}/ocp/{ocp_idx}",
                    id=ocp_idx,
                    rid=pdu_ocps[ocp_idx].target,
                    inlet_rid=inlet.target,
                    name=ocp_settings.name,
                    label=ocp_metadata.label,
                    sensors=RaritanPduOverCurrentProtectorSensors.from_sensor_sources(
                        {
                            "trip": ocp_sensors.trip,
                            "voltage": ocp_sensors.voltage,
                            "current": ocp_sensors.current,
                            "peak_current": ocp_sensors.peakCurrent,
                            "maximum_current": ocp_sensors.maximumCurrent,
                            "active_power": ocp_sensors.activePower,
                            "reactive_power": ocp_sensors.reactivePower,
                            "apparent_power": ocp_sensors.apparentPower,
                            "power_factor": ocp_sensors.powerFactor,
                            "displacement_power_factor": ocp_sensors.displacementPowerFactor,
                            "crest_factor": ocp_sensors.crestFactor,
                            "active_energy": ocp_sensors.activeEnergy,
                            "apparent_energy": ocp_sensors.apparentEnergy,
                            "line_frequency": ocp_sensors.lineFrequency,
                            "phase_angle": ocp_sensors.phaseAngle,
                            "residual_current": ocp_sensors.residualCurrent,
                            "residual_ac_current": ocp_sensors.residualACCurrent,
                            "residual_dc_current": ocp_sensors.residualDCCurrent,
                            "residual_current_status": ocp_sensors.residualCurrentStatus,
                        }
                    ),
                )

                ocps.append(pdu.add_ocp(ocp))
        except rpc.HttpException as e:
            self._logger.exception("Error fetching PDU overcurrent protectors")

            message: str = f"Failed to fetch PDU overcurrent protectors for {self._config.host}"
            raise RaritanClientError(message) from e
        else:
            return ocps

    async def _update_sensors_for_device(
        self, device: RaritanDevice, device_sensors: list[tuple[str, str, RaritanSensor]], update_type: _SensorUpdate
    ) -> None:
        update_requests = [
            (device_name, (device_name, sensor_name), request, update)
            for (device_name, sensor_name, sensor) in device_sensors
            for (request, update) in update_type.get_update_methods(sensor)
        ]

        devices, sensors, requests, update_methods = [list(tup) for tup in zip(*update_requests, strict=True)]

        responses = await self._execute_bulk_requests(
            interleave(requests),
            update_type.fetch_msg(device, len(set(devices)), len(set(sensors))),
        )

        for response, method in zip(responses, update_methods, strict=True):
            method(response)

    async def _update_sensor_info_for_device(self, device: RaritanDevice_co) -> RaritanDevice_co:
        await self._update_sensors_for_device(device, device.updatable_sensors, _SensorUpdate.INFO)

        return device

    async def _update_all_sensor_info_for_device(self, device: RaritanDevice_co) -> RaritanDevice_co:
        await self._update_sensors_for_device(device, device.all_updatable_sensors, _SensorUpdate.INFO)

        return device

    async def update_sensor_readings_for_device(self, device: RaritanDevice_co) -> RaritanDevice_co:
        """Update sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(device, device.updatable_sensors, _SensorUpdate.READINGS)

        return device

    async def update_sensor_readings_for_devices(
        self, pdu: RaritanPdu, devices: list[RaritanDevice_co]
    ) -> list[RaritanDevice_co]:
        """Update sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(
            pdu,
            list(flatten([device.updatable_sensors for device in devices])),
            _SensorUpdate.READINGS,
        )

        return devices

    async def update_all_sensor_readings_for_device(self, device: RaritanDevice_co) -> RaritanDevice_co:
        """Update all sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(device, device.all_updatable_sensors, _SensorUpdate.READINGS)

        return device

    async def update_sensor_readings_for_pdu(self, pdu: RaritanPdu) -> RaritanPdu:
        """Update all sensor readings for PDU."""
        return await self.update_all_sensor_readings_for_device(pdu)

    async def set_outlet_power_state(
        self,
        pdu_idx: int = 0,
        outlet_idx: int = 0,
        state: OutletPowerState = OutletPowerState.ON,
    ) -> OutletPowerState:
        """Get the power state for a specific Raritan PDU outlet."""
        await self.authenticate()

        try:
            outlet = Outlet(f"/model/pdu/{pdu_idx}/outlet/{outlet_idx}", self._agent)

            status: int = await self._hass.async_add_executor_job(
                outlet.setPowerState, STATE_TO_API_MAPPING[OutletPowerState][state]
            )

            self._logger.debug("Changed PDU %s outlet %s state to %s", pdu_idx, outlet_idx, state.name)
        except rpc.HttpException as e:
            self._logger.exception("Error setting PDU %s outlet %s power state", pdu_idx, outlet_idx)

            msg: str = f"Failed to set PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"
            raise RaritanClientError(msg) from e
        else:
            match status:
                case 0:  # OK
                    return state
                case Outlet.ERR_OUTLET_NOT_SWITCHABLE:
                    msg = f"PDU {pdu_idx} outlet {outlet_idx} not switchable for {self._config.host}"
                case Outlet.ERR_OUTLET_DISABLED:
                    msg = f"PDU {pdu_idx} outlet {outlet_idx} disabled for {self._config.host}"
                case Outlet.ERR_RELAY_CONTROL_DISABLED:
                    msg = f"PDU {pdu_idx} outlet {outlet_idx} relay control disabled for {self._config.host}"
                case _:
                    msg = f"Unexpected response setting PDU {pdu_idx} outlet {outlet_idx} power state for {self._config.host}"  # noqa: E501

            raise RaritanClientError(msg)


class RaritanClientError(Exception):
    """Base exception for all client exceptions."""


class ConfigError(RaritanClientError):
    """Raised when configuration is invalid."""


class CommunicationError(RaritanClientError):
    """Raised when a generic error occurs while communicating with the Raritan API."""


class CertificateVerificationError(CommunicationError):
    """Raised when SSL certificate verification fails."""


class AuthenticationError(CommunicationError):
    """Raised when authentication fails."""


class SessionError(CommunicationError):
    """Raised when session operations fail."""


class ConcurrentLoginError(AuthenticationError, SessionError):
    """Raised when creation of a new session fails due single login limitation."""


class SessionCloseError(SessionError):
    """Raised when closing the current session."""
