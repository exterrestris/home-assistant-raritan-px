"""API client for Raritan PX devices."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from ssl import SSLCertVerificationError
from typing import TYPE_CHECKING, Any, Final

from more_itertools import flatten, grouper, interleave
from raritan import rpc
from raritan.rpc import Structure, Time, perform_bulk
from raritan.rpc.cascading import CascadeManager
from raritan.rpc.firmware import (
    Firmware,
    FirmwareUpdateStatus,
    ImageInfo,
    ImageState,
    ImageStatus,
    UpdateStatus,
)
from raritan.rpc.firmware import (
    upload as firmware_upload,
)
from raritan.rpc.net import Info, InterfaceInfo, Net
from raritan.rpc.pdumodel import Inlet, Outlet, OverCurrentProtector, Pdu
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import Role, RoleManager, User, UserInfo

from custom_components.raritan_px.api.client.connections import Connection, ConnectionManager
from custom_components.raritan_px.api.client.const import (
    FIRMWARE_UPDATE_CHECK_CACHE_RESULT_FOR,
    FIRMWARE_UPDATE_PREVENT_CHECKS_AFTER_START_FOR,
    FIRMWARE_UPGRADE_SUCCESS_WAIT_INTERVAL,
    FIRMWARE_UPGRADE_WAIT_INTERVAL,
    FIRMWARE_UPGRAGE_WAIT_MAX_ERRORS,
    PduDevices,
    SensorUpdate,
    UpdateSensors,
)
from custom_components.raritan_px.api.client.decorators import Authenticate, Retry
from custom_components.raritan_px.api.client.errors import (
    AuthenticationError,
    CertificateVerificationError,
    CommunicationError,
    ConcurrentLoginError,
    ConfigError,
    FirmwareUpgradeFailedError,
    FirmwareUpgradeInProgressError,
    FirmwareVerificationError,
    ForbiddenError,
    HttpError,
    IncompatibleFirmwareError,
    InsufficientPrivilegesError,
    InvalidFirmwareError,
    JsonRpcDecodeError,
    JsonRpcError,
    NoFirmwareUpgradeInProgressError,
    NoUploadedFirmwareError,
    RaritanClientError,
    RequestError,
    RequestRefusedError,
    RequestTimeoutError,
    SessionCloseError,
    UnauthorizedError,
    UnsupportedModelFirmwareError,
)
from custom_components.raritan_px.api.const import FIRMWARE_UPLOAD_TIMEOUT, PING_TIMEOUT
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
from custom_components.raritan_px.api.model.network import (
    NetworkInterface,
    NetworkInterfaceState,
    NetworkInterfaceType,
)
from custom_components.raritan_px.api.model.user import Privilege, RaritanUser
from custom_components.raritan_px.utils import LockManager
from custom_components.raritan_px.utils.decorators import LogExecutionTime

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from homeassistant.core import HomeAssistant

    from custom_components.raritan_px.api.client.struct import ConnectionDetails
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState
    from custom_components.raritan_px.api.model.sensor import RaritanSensor

_LOGGER = logging.getLogger(__name__)


class RaritanClient:
    """Client for Raritan API."""

    _REQUEST: Final[str] = "request"
    _FW_STATUS: Final[str] = "fw_status"
    _FW_UPLOAD: Final[str] = "fw_upload"
    _PING: Final[str] = "ping"
    _AUTH_LOCK: Final[str] = "auth"

    _hass: HomeAssistant
    _connections: ConnectionManager
    _locks: LockManager
    _config: ConnectionDetails
    _firmware_update_in_progress: bool | None = None
    _firmware_update_recheck_after: datetime | None = None

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
        self._logger = logger = logger or _LOGGER
        self._locks = LockManager()
        self._connections = ConnectionManager(config=config, logger=self._logger)

    @property
    def _connection(self) -> Connection:
        return self._connections.get(self._REQUEST)

    async def _execute_json_rpc_call(self, *args: Any) -> Any:
        def raise_original_exception(e: rpc.HttpException) -> None:
            try:
                previous = e.args[1]
            except IndexError:
                return
            else:
                if not isinstance(e.args[1], Exception):
                    return

            raise previous

        def raise_from_rpc_http_exception(err: rpc.HttpException) -> None:
            if err.args and (matched := re.match(r"HTTP Error (?P<code>[0-9]{3})", str(err.args[0]))):
                code = int(matched.group("code"))
                match code:
                    case 401:
                        raise UnauthorizedError from err
                    case 403:
                        raise ForbiddenError from err
                    case _:
                        raise HttpError(code=code) from err

            raise HttpError(code=None) from err

        try:
            response = await self._hass.async_add_executor_job(*args)
        except rpc.HttpException as err:
            try:
                raise_original_exception(err)
            except SSLCertVerificationError as e:
                raise CertificateVerificationError from e
            except TimeoutError as e:
                raise RequestTimeoutError from e
            except ConnectionRefusedError as e:
                raise RequestRefusedError from e
            except Exception as e:
                raise RequestError from e
            else:
                raise_from_rpc_http_exception(err)
        except rpc.JsonRpcErrorException as err:
            if "code = -32001" in str(err):
                raise InsufficientPrivilegesError from err

            raise JsonRpcError from err
        except rpc.JsonRpcSyntaxException as err:
            raise CommunicationError from err
        except rpc.DecodeException as err:
            raise JsonRpcDecodeError from err
        return response

    async def _execute_bulk_requests(
        self, requests: list[tuple[rpc.Interface.Method, list[Any]]], data_name: str | Callable[[], str] | None = None
    ) -> list[Structure]:
        async with self._connection.lock:
            let = LogExecutionTime(
                f"Fetched {data_name() if callable(data_name) else data_name} via {len(requests)} requests",
                logger=self._logger,
            )
            return await let.wrap(self._execute_json_rpc_call(perform_bulk, self._connection.agent, requests, True))  # noqa: FBT003

    async def _execute_request(self, request: rpc.Interface.Method, *args: Any, timed: bool = False) -> Any:
        async with self._connection.lock:
            if timed:
                let = LogExecutionTime(
                    f"Executed '{request.name}' request against '{request.parent.target}'"  # pyright: ignore[reportAttributeAccessIssue]
                )
                return await let.wrap(self._execute_json_rpc_call(request, *args))

            return await self._execute_json_rpc_call(request, *args)

    async def ping(self, *, raise_exception: bool = False) -> bool:
        """Ping the API to determine if it can be reached without timing out."""
        try:
            status = await self._get_firmware_update_status(self._connections.get(self._PING, timeout=PING_TIMEOUT))
        except RequestTimeoutError:
            if raise_exception:
                raise

            return False
        else:
            return bool(status.state in {"NONE", "SUCCESS", "FAIL"})

    async def authenticate(self, *, force_reauth: bool = False) -> None:
        """Authenticate with the Raritan API, using either an existing session token or username/password."""
        await self._check_if_firmware_update_in_progress()

        await self._authenticate(self._connection, force_reauth=force_reauth)

    async def _authenticate(self, connection: Connection, *, force_reauth: bool = False) -> None:
        async with self._locks.get(self._AUTH_LOCK):
            if connection.session_token is not None:
                await self._authenticate_with_token(connection, force_reauth=force_reauth)

            if connection.session_token is None:
                await self._authenticate_with_credentials(connection)

    async def _authenticate_with_token(self, connection: Connection, *, force_reauth: bool = False) -> None:
        if connection.config.auth is None:
            message: str = f"No authentication information provided for {connection.config.host}"
            raise AuthenticationError(message)

        try:
            connection.set_auth_from_token()

            session_details: Session = await self._execute_request(connection.session_manager.getCurrentSession)

            if session_details.username != connection.config.auth.user:
                force_reauth = True

                self._logger.warning(
                    "User %s attempting to use session token for user %s to authenticate with %s",
                    connection.config.auth.user,
                    session_details.username,
                    connection.config.host,
                )

            if force_reauth:
                try:
                    self._logger.info(
                        "Closing existing session on %s and forcing re-authentication",
                        connection.config.host,
                    )

                    await self._close_connection_session(
                        connection,
                        session_details,
                        SessionManager.CloseReason.CLOSE_REASON_FORCED_DISCONNECT,  # pyright: ignore[reportAttributeAccessIssue]
                    )
                except SessionCloseError:
                    # This has already been logged
                    pass
                finally:
                    connection.clear_session_data()
            else:
                await self._execute_request(connection.session_manager.touchCurrentSession, True)  # noqa: FBT003

                self._logger.debug(
                    "Authenticated with %s using session token for %s, session created at %s",
                    connection.config.host,
                    session_details.username,
                    connection.session_created,
                )
        except RequestError:
            connection.clear_session_data()

            self._logger.debug(
                "Session token for %s has expired, will attempt to authenticate using credentials",
                connection.config.host,
            )

    async def _authenticate_with_credentials(self, connection: Connection) -> None:
        if connection.config.auth is None:
            msg: str = f"No authentication information provided for {connection.config.host}"
            raise AuthenticationError(msg)

        try:
            response: int

            connection.set_auth_from_credentials()

            user = connection.proxy(User, "/auth/currentUser")
            user_info: UserInfo = await self._execute_request(user.getInfo)

            self._logger.info(
                "Authenticated with %s as %s (%s)",
                connection.config.host,
                connection.config.auth.user,
                user_info.auxInfo.fullname,
            )

            session_details: Session

            (
                response,
                session_details,
                connection.session_token,
            ) = await self._execute_request(connection.session_manager.newSession)

            if response == SessionManager.ERR_ACTIVE_SESSION_EXCLUSIVE_FOR_USER:
                msg: str = (
                    f"Failed to create new session on {connection.config.host}"
                    f"for logged-in user {connection.config.auth.user}"
                )
                raise ConcurrentLoginError(msg)

            # The Raritan JSON-RPC API returns the session created time as a timestamp in microseconds relative to
            # system boot, however the Raritan Python SDK creates a datetime instance from that value as if it were
            # a POSIX timestamp. To get an accurate creation time, we need to undo this
            session_creation: Time = session_details.creationTime  # pyright: ignore[reportAssignmentType]
            connection.session_created = datetime.now(UTC) - timedelta(microseconds=session_creation.timestamp())

            self._logger.debug(
                "Session created for %s on %s at %s",
                session_details.username,
                connection.config.host,
                connection.session_created,
            )
        except CertificateVerificationError:
            self._logger.exception("Authentication Error")
            raise
        except RequestError as e:
            self._logger.exception("Authentication Error")

            msg: str = f"Failed to authenticate as {connection.config.auth.user} on {connection.config.host}"
            raise AuthenticationError(msg) from e

    async def _close_connection_session(
        self, connection: Connection, session_details: Session, reason: SessionManager.CloseReason
    ) -> bool:
        try:
            connection.set_auth_from_token()

            self._logger.debug(
                "Closing session for %s on %s created at %s",
                session_details.username,
                connection.config.host,
                connection.session_created,
            )

            await self._execute_request(connection.session_manager.closeCurrentSession, reason)
        except rpc.HttpException as err:
            self._logger.warning(
                "Failed to close existing session for %s on %s",
                session_details.username,
                connection.config.host,
                exc_info=True,
            )

            raise SessionCloseError from err
        else:
            self._logger.info(
                "Session closed for %s on %s",
                session_details.username,
                connection.config.host,
            )
        finally:
            connection.clear_session_data()

        return True

    async def _close_session(self, connection: Connection) -> bool:
        if connection.session_token is None:
            self._logger.debug("No active session to close")
            return False

        try:
            await self._check_if_firmware_update_in_progress()

            async with self._locks.get(self._AUTH_LOCK):
                connection.set_auth_from_token()

                session_details: Session = await self._execute_request(connection.session_manager.getCurrentSession)

                return await self._close_connection_session(
                    connection,
                    session_details,
                    SessionManager.CloseReason.CLOSE_REASON_LOGOUT,  # pyright: ignore[reportAttributeAccessIssue]
                )
        except FirmwareUpgradeInProgressError:
            self._logger.debug("Session closed by firmware update", exc_info=True)

            return False
        except rpc.HttpException:
            self._logger.debug("Session expired before close request", exc_info=True)
        finally:
            connection.clear_session_data()

        return True

    @Authenticate()
    async def get_privileges(self) -> list[Privilege]:
        """Get all privileges."""
        role: RoleManager = self._connection.proxy(RoleManager, "/auth/role")
        privileges: list[Role.Privilege] = await self._execute_request(role.getAllPrivileges)

        return [Privilege(privilege) for privilege in privileges]

    @Authenticate()
    async def get_user(self, username: str | None = None) -> RaritanUser:
        """Get user information and privileges."""
        proxy: User = self._connection.proxy(User, f"/auth/user/{username}" if username else "/auth/currentUser")
        info: UserInfo
        privileges: list[Role.Privilege]

        (info, privileges) = await self._execute_request(proxy.getInfoAndPrivileges)

        user = RaritanUser.from_rpc(info, privileges)

        if user.unknown_privileges:
            self._logger.warning(
                "User has unsupported privileges: %s", ", ".join([str(priv) for priv in user.unknown_privileges])
            )

        return user

    async def close_session(self) -> bool:
        """Close the current session and clear any stored session information."""
        return await self._close_session(self._connection)

    @Authenticate()
    async def get_pdu_info(
        self,
        pdu_idx: int = 0,
        *,
        populate: PduDevices = PduDevices.ALL,
        update: UpdateSensors = UpdateSensors.ALL,
    ) -> RaritanPdu:
        """Get information for the Raritan PDU."""
        try:
            pdu: Pdu = self._connection.proxy(Pdu, f"/model/pdu/{pdu_idx}")
            firmware: Firmware = self._connection.proxy(Firmware, "/firmware")
            cascade = self._connection.proxy(CascadeManager, "/cascade")
            net = self._connection.proxy(Net, "/net")

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
                    (firmware.getInfo, []),
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
            firmware_info: Firmware.Info = responses[8]  # pyright: ignore[reportAssignmentType]
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
                    type=NetworkInterfaceType.from_api(interface.type),
                    enabled=interface.enabled,
                    state=NetworkInterfaceState.from_api(interface.state),
                    mac_address=interface.macAddr,
                )
                for key, interface in interfaces.items()
            }

            device = RaritanPdu(
                device_id=f"{pdu_metadata.nameplate.serialNumber}:/model/pdu/{pdu_idx}",
                rid=pdu.target,
                id=pdu_idx,
                host=self._config.host,
                url=f"{self._config.protocol}://{self._config.host}/",
                name=psu_settings.name,
                manufacturer=pdu_metadata.nameplate.manufacturer,
                model=pdu_metadata.nameplate.model,
                platform=firmware_info.platform,
                serial_number=pdu_metadata.nameplate.serialNumber,
                firmware_version=firmware_info.version,
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

            if (populate & PduDevices.OUTLETS) and pdu_outlets:
                await self._get_outlets_info(pdu_outlets, device, pdu_metadata.nameplate.serialNumber)

            if (populate & PduDevices.INLETS) and pdu_inlets:
                await self._get_inlets_info(pdu_inlets, device, pdu_metadata.nameplate.serialNumber)

            if (populate & PduDevices.OCPS) and pdu_ocps:
                await self._get_ocps_info(pdu_ocps, device, pdu_metadata.nameplate.serialNumber)

            if update & UpdateSensors.INFO:
                await self._update_all_sensor_info_for_device(device)

            if update & UpdateSensors.READINGS:
                await self.update_all_sensor_readings_for_device(device)

            return device

    async def _get_outlets_info(
        self, pdu_outlets: list[Outlet], pdu: RaritanPdu, pdu_serial: str
    ) -> list[RaritanPduOutlet]:
        if not pdu_outlets:
            return []

        try:
            responses = await self._execute_bulk_requests(
                list(
                    interleave(
                        [(outlet.getMetaData, []) for outlet in pdu_outlets],
                        [(outlet.getSettings, []) for outlet in pdu_outlets],
                        [(outlet.getSensors, []) for outlet in pdu_outlets],
                        [(outlet.getIOP, []) for outlet in pdu_outlets],
                    )
                ),
                f"outlet data for PDU {pdu.id}",
            )

            outlets: list[RaritanPduOutlet] = []

            outlet_metadata: Outlet.MetaData
            outlet_settings: Outlet.Settings
            outlet_sensors: Outlet.Sensors
            inlet: Inlet | None
            ocp: OverCurrentProtector | None

            for outlet_idx, (
                outlet_metadata,
                outlet_settings,
                outlet_sensors,
                (inlet, ocp, _),
            ) in enumerate(grouper(responses, 4)):  # pyright: ignore[reportGeneralTypeIssues, reportAssignmentType]
                outlet = RaritanPduOutlet(
                    device_id=f"{pdu_serial}:/model/pdu/{pdu.id}/outlet/{outlet_idx}",
                    rid=pdu_outlets[outlet_idx].target,
                    inlet_rid=inlet.target if inlet else None,
                    ocp_rid=ocp.target if ocp else None,
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
        if not pdu_inlets:
            return []

        try:
            responses = await self._execute_bulk_requests(
                list(
                    interleave(
                        [(inlet.getMetaData, []) for inlet in pdu_inlets],
                        [(inlet.getSettings, []) for inlet in pdu_inlets],
                        [(inlet.getSensors, []) for inlet in pdu_inlets],
                    )
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
        if not pdu_ocps:
            return []

        try:
            responses = await self._execute_bulk_requests(
                list(
                    interleave(
                        [(ocp.getMetaData, []) for ocp in pdu_ocps],
                        [(ocp.getSettings, []) for ocp in pdu_ocps],
                        [(ocp.getSensors, []) for ocp in pdu_ocps],
                        [(ocp.getInlet, []) for ocp in pdu_ocps],
                    )
                ),
                f"ocp data for PDU {pdu.id}",
            )

            ocps: list[RaritanPduOverCurrentProtector] = []

            ocp_metadata: OverCurrentProtector.MetaData
            ocp_settings: OverCurrentProtector.Settings
            ocp_sensors: OverCurrentProtector.Sensors
            inlet: Inlet | None

            for ocp_idx, (ocp_metadata, ocp_settings, ocp_sensors, inlet) in enumerate(grouper(responses, 4)):  # pyright: ignore[reportAssignmentType]
                ocp = RaritanPduOverCurrentProtector(
                    device_id=f"{pdu_serial}:/model/pdu/{pdu.id}/ocp/{ocp_idx}",
                    id=ocp_idx,
                    rid=pdu_ocps[ocp_idx].target,
                    inlet_rid=inlet.target if inlet else None,
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
        self, device: RaritanDevice, device_sensors: list[tuple[str, str, RaritanSensor]], update_type: SensorUpdate
    ) -> None:
        update_requests = [
            (device_name, (device_name, sensor_name), request, update)
            for (device_name, sensor_name, sensor) in device_sensors
            for (request, update) in update_type.get_update_methods(sensor)
        ]

        devices, sensors, requests, update_methods = [list(tup) for tup in zip(*update_requests, strict=True)]

        responses = await self._execute_bulk_requests(
            list(interleave(requests)),
            update_type.fetch_msg(device, len(set(devices)), len(set(sensors))),
        )

        for response, method in zip(responses, update_methods, strict=True):
            method(response)

    async def _update_sensor_info_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        await self._update_sensors_for_device(device, device.updatable_sensors, SensorUpdate.INFO)

        return device

    async def _update_all_sensor_info_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        await self._update_sensors_for_device(device, device.all_updatable_sensors, SensorUpdate.INFO)

        return device

    @Authenticate()
    async def update_sensor_readings_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        """Update sensor readings for device."""
        await self._update_sensors_for_device(device, device.updatable_sensors, SensorUpdate.READINGS)

        return device

    @Authenticate()
    async def update_sensor_readings_for_devices[Device: "RaritanDevice"](
        self, pdu: RaritanPdu, devices: list[Device]
    ) -> list[Device]:
        """Update sensor readings for device."""
        await self._update_sensors_for_device(
            pdu,
            list(flatten([device.updatable_sensors for device in devices])),
            SensorUpdate.READINGS,
        )

        return devices

    @Authenticate()
    async def update_all_sensor_readings_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        """Update all sensor readings for device."""
        await self._update_sensors_for_device(device, device.all_updatable_sensors, SensorUpdate.READINGS)

        return device

    async def update_sensor_readings_for_pdu(self, pdu: RaritanPdu) -> RaritanPdu:
        """Update all sensor readings for PDU."""
        return await self.update_all_sensor_readings_for_device(pdu)

    @Authenticate()
    async def refresh_pdu_firmware_version(self, pdu: RaritanPdu) -> RaritanPdu:
        """Update the PDU model with the current firmware version."""
        proxy: Firmware = self._connection.proxy(Firmware, "/firmware")
        firmware_info: Firmware.Info = await self._execute_request(proxy.getInfo)

        pdu.firmware_version = firmware_info.version

        return pdu

    @Authenticate()
    async def set_outlet_power_state(self, outlet: RaritanPduOutlet, state: OutletPowerState) -> OutletPowerState:
        """Get the power state for a specific Raritan PDU outlet."""
        try:
            proxy = self._connection.proxy(Outlet, outlet.rid)

            status: int = await self._execute_request(proxy.setPowerState, state.to_api())

            self._logger.debug("Changed PDU %s outlet %s state to %s", outlet.pdu.id, outlet.id, state.name)
        except rpc.HttpException as e:
            self._logger.exception("Error setting PDU %s outlet %s power state", outlet.pdu.id, outlet.id)

            msg: str = f"Failed to set PDU {outlet.pdu.id} outlet {outlet.id} power state for {self._config.host}"
            raise RaritanClientError(msg) from e
        else:
            match status:
                case 0:  # OK
                    return state
                case Outlet.ERR_OUTLET_NOT_SWITCHABLE:
                    msg = f"PDU {outlet.pdu.id} outlet {outlet.id} not switchable for {self._config.host}"
                case Outlet.ERR_OUTLET_DISABLED:
                    msg = f"PDU {outlet.pdu.id} outlet {outlet.id} disabled for {self._config.host}"
                case Outlet.ERR_RELAY_CONTROL_DISABLED:
                    msg = f"PDU {outlet.pdu.id} outlet {outlet.id} relay control disabled for {self._config.host}"
                case _:
                    msg = f"Unexpected response setting PDU {outlet.pdu.id} outlet {outlet.id} power state for {self._config.host}"  # noqa: E501

            raise RaritanClientError(msg)

    @Authenticate()
    async def upload_firmware(self, firmware: Path) -> None:
        """Upload firmware to the PDU."""

        @LogExecutionTime("Uploaded firmware", logger=self._logger)
        def _upload_firmware(agent: rpc.Agent, firmware: Path) -> None:
            firmware_upload(agent, firmware.read_bytes())

        proxy = self._connection.proxy(Firmware, "/firmware")
        status: ImageStatus = await self._execute_request(proxy.getImageStatus)

        if status.state != ImageState.NONE:  # pyright: ignore[reportAttributeAccessIssue]
            await self._execute_request(proxy.discardImage)

        try:
            # Firmware uploads take longer to complete that the default request timeout
            # so create a new agent instance for the firmware upload, reusing the existing
            # session token from the default agent, and use a dedicated lock for this request
            connection = self._connections.get(self._FW_UPLOAD, timeout=FIRMWARE_UPLOAD_TIMEOUT)
            connection.session_token = self._connection.session_token
            connection.set_auth_from_token()

            async with connection.lock:
                await self._execute_json_rpc_call(_upload_firmware, connection.agent, firmware)

            await self._verify_firmware()
        except:
            await self._execute_request(proxy.discardImage)

            raise

    async def _verify_firmware(self) -> None:
        image_info: ImageInfo | None = await self.get_uploaded_firmware_info()

        if not image_info:
            raise NoUploadedFirmwareError

        if not image_info.valid:
            raise InvalidFirmwareError

        if not image_info.compatible:
            raise IncompatibleFirmwareError

        if image_info.model_list_present and not image_info.model_supported:
            raise UnsupportedModelFirmwareError

    @Authenticate()
    async def get_firmware_upload_status(self) -> bool | float | str | None:
        """Get information about the current uploaded firmware."""
        proxy = self._connection.proxy(Firmware, "/firmware")
        status: ImageStatus = await self._execute_request(proxy.getImageStatus)

        match status.state:
            case ImageState.NONE:  # pyright: ignore[reportAttributeAccessIssue]
                return None
            case ImageState.UPLOADING, ImageState.DOWNLOADING:  # pyright: ignore[reportAttributeAccessIssue]
                return status.size_done / status.size_total * 100 if status.size_total else 0
            case ImageState.UPLOAD_FAILED, ImageState.DOWNLOAD_FAILED:  # pyright: ignore[reportAttributeAccessIssue]
                return status.error_message or False
            case ImageState.COMPLETE:  # pyright: ignore[reportAttributeAccessIssue]
                return True

    @Authenticate()
    async def get_uploaded_firmware_info(self) -> ImageInfo | None:
        """Get information about the current uploaded firmware."""
        proxy = self._connection.proxy(Firmware, "/firmware")
        image_present: bool
        image_info: ImageInfo
        (image_present, image_info) = await self._execute_request(proxy.getImageInfo)

        if not image_present:
            return None

        return image_info

    @Authenticate()
    async def cancel_firmware_update(self) -> None:
        """Start the firmaware update on the PDU."""
        proxy = self._connection.proxy(Firmware, "/firmware")

        await self._execute_request(proxy.discardImage)

        self._update_firmware_update_in_progress(status=False)

    @Authenticate()
    async def start_firmware_update(self) -> None:
        """Start the firmaware update on the PDU."""
        proxy = self._connection.proxy(Firmware, "/firmware")

        try:
            await self._verify_firmware()
        except FirmwareVerificationError:
            await self._execute_request(proxy.discardImage)
            raise
        else:
            await self._execute_request(proxy.startUpdate, [])

            self._update_firmware_update_in_progress(
                status=True, cache_for=FIRMWARE_UPDATE_PREVENT_CHECKS_AFTER_START_FOR
            )

    async def _get_firmware_update_status(self, connection: Connection) -> UpdateStatus:
        # Endpoint is always available and doesn't require authentication, but if invalid credentials
        # or an expired session token are supplied the request will fail as unauthorised
        proxy: FirmwareUpdateStatus = connection.proxy(FirmwareUpdateStatus, "/cgi-bin/fwupdate_progress.cgi")

        async with connection.lock:
            status: UpdateStatus = await self._execute_json_rpc_call(proxy.getStatus)

        return status

    @Retry(catch=(RequestRefusedError, RequestTimeoutError), max_retries=8)
    async def get_firmware_update_status(self) -> UpdateStatus:
        """Get the current firmware update status."""
        return await self._get_firmware_update_status(self._connections.get(self._FW_STATUS))

    async def _check_firmware_update_progress(self) -> bool:
        status: UpdateStatus = await self.get_firmware_update_status()

        match status.state:
            case "NONE":
                return False
            case "SUCCESS":
                return True
            case "FAIL":
                raise FirmwareUpgradeFailedError(status.error_message)
            case _:
                raise FirmwareUpgradeInProgressError(status.state, status.elapsed, status.estimated)

    async def _check_if_firmware_update_in_progress(
        self,
        *,
        force_check: bool = False,
        wait_for: float = 0,
        raise_in_progress: bool = True,
    ) -> bool:
        async with self._locks.get(self._FW_STATUS):
            if self._firmware_update_recheck_after is None or self._firmware_update_recheck_after < datetime.now(UTC):
                force_check = True

            if self._firmware_update_in_progress is None or force_check:
                self._logger.debug("Checking firmware update status for %s", self._config.host)

                try:
                    await self._check_firmware_update_progress()
                    return self._update_firmware_update_in_progress(status=False)
                except FirmwareUpgradeFailedError:
                    return self._update_firmware_update_in_progress(status=False)
                except FirmwareUpgradeInProgressError:
                    self._update_firmware_update_in_progress(status=True)

                    if wait_for:
                        await asyncio.sleep(wait_for)
                        return await self._check_if_firmware_update_in_progress(force_check=True)

                    if raise_in_progress:
                        raise

                    return True

            return self._firmware_update_in_progress

    def _update_firmware_update_in_progress(
        self, *, status: bool, cache_for: timedelta = FIRMWARE_UPDATE_CHECK_CACHE_RESULT_FOR
    ) -> bool:
        self._firmware_update_in_progress = status
        self._firmware_update_recheck_after = datetime.now(UTC) + cache_for

        return self._firmware_update_in_progress

    async def is_firmware_update_in_progress(self, *, force_check: bool = False) -> bool:
        """Check if a firmware update is in progress."""
        return await self._check_if_firmware_update_in_progress(force_check=force_check, raise_in_progress=False)

    async def wait_for_firmware_update(self) -> bool:
        """Wait for the current firmware update to complete."""
        errors = 0

        while True:
            try:
                if (success := await self._check_firmware_update_progress()) is None:
                    raise NoFirmwareUpgradeInProgressError
            except FirmwareUpgradeInProgressError as err:
                wait: float = FIRMWARE_UPGRADE_WAIT_INTERVAL

                if err.estimated and err.elapsed:
                    wait = err.estimated - err.elapsed

                await asyncio.sleep(wait)
            except RequestError:
                if (errors := errors + 1) > FIRMWARE_UPGRAGE_WAIT_MAX_ERRORS:
                    raise

                await asyncio.sleep(FIRMWARE_UPGRADE_WAIT_INTERVAL)
            else:
                if success:
                    await asyncio.sleep(FIRMWARE_UPGRADE_SUCCESS_WAIT_INTERVAL)

                return success
