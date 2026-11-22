"""API client for Raritan PX devices."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import UTC, datetime, timedelta
from ssl import SSLCertVerificationError
from typing import TYPE_CHECKING, Any

from more_itertools import flatten, grouper, interleave
from raritan import rpc
from raritan.rpc import Structure, Time, perform_bulk
from raritan.rpc.cascading import CascadeManager
from raritan.rpc.net import Info, InterfaceInfo, Net
from raritan.rpc.pdumodel import Inlet, Outlet, OverCurrentProtector, Pdu
from raritan.rpc.session import Session, SessionManager
from raritan.rpc.usermgmt import User, UserInfo

from custom_components.raritan_px.api.client.const import (
    PduDevices,
    SensorUpdate,
    UpdateSensors,
)
from custom_components.raritan_px.api.client.errors import (
    AuthenticationError,
    CertificateVerificationError,
    CommunicationError,
    ConcurrentLoginError,
    ConfigError,
    HttpError,
    InsufficientPrivilegesError,
    JsonRpcDecodeError,
    JsonRpcError,
    RaritanClientError,
    RequestTimeoutError,
    SessionCloseError,
)
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
from custom_components.raritan_px.utils.decorators import LogExecutionTime

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from custom_components.raritan_px.api.client.struct import ConnectionDetails
    from custom_components.raritan_px.api.model.device import RaritanDevice
    from custom_components.raritan_px.api.model.device.pdu.outlet.state import OutletPowerState
    from custom_components.raritan_px.api.model.sensor import RaritanSensor

_LOGGER = logging.getLogger(__name__)


class RaritanClient:
    """Client for Raritan API."""

    _REQUEST = "request"
    _FIRMWARE_STATUS = "fw_status"
    _FIRMWARE_UPLOAD = "fw_upload"
    _AUTH_LOCK = "auth"

    _hass: HomeAssistant
    _agents: dict[str, rpc.Agent]
    _locks: dict[str, Lock]
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
        self._agents = {}
        self._locks = {}
        self._session_manager = SessionManager("/session", self._agent)

        if logger is not None:
            self._logger = logger

    @property
    def _agent(self) -> rpc.Agent:
        return self._get_agent(self._REQUEST)

    def _get_agent(self, name: str, timeout: int | None = None) -> rpc.Agent:
        if name not in self._agents:
            self._agents[name] = rpc.Agent(
                self._config.protocol,
                f"{self._config.host}:{self._config.port}",
                disable_certificate_verification=not self._config.verify_ssl,
                timeout=timeout or self._config.timeout,
            )

        return self._agents[name]

    def _get_lock(self, name: str) -> Lock:
        if name not in self._locks:
            self._locks[name] = Lock()

        return self._locks[name]

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

        try:
            response = await self._hass.async_add_executor_job(*args)
        except rpc.HttpException as err:
            try:
                raise_original_exception(err)
            except SSLCertVerificationError as e:
                raise CertificateVerificationError from e
            except TimeoutError as e:
                raise RequestTimeoutError from e
            except Exception as e:
                raise HttpError from e
            else:
                raise HttpError from err
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
        async with self._get_lock(self._REQUEST):
            let = LogExecutionTime(
                f"Fetched {data_name() if callable(data_name) else data_name} via {len(requests)} requests",
                logger=self._logger,
            )
            return await let.wrap(self._execute_json_rpc_call(perform_bulk, self._agent, requests))

    async def _execute_request(self, request: rpc.Interface.Method, *args: Any, timed: bool = False) -> Any:
        async with self._get_lock(self._REQUEST):
            if timed:
                let = LogExecutionTime(
                    f"Executed '{request.name}' request against '{request.parent.target}'"  # pyright: ignore[reportAttributeAccessIssue]
                )
                return await let.wrap(self._execute_json_rpc_call(request, *args))

            return await self._execute_json_rpc_call(request, *args)

    async def authenticate(self, *, force_reauth: bool = False) -> None:
        """Authenticate with the Raritan API, using either an existing session token or username/password."""
        async with self._get_lock(self._AUTH_LOCK):
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

            session_details: Session = await self._execute_request(self._session_manager.getCurrentSession)

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
                await self._execute_request(self._session_manager.touchCurrentSession, True)  # noqa: FBT003

                self._logger.debug(
                    "Authenticated with %s using session token for %s, session created at %s",
                    self._config.host,
                    session_details.username,
                    self._session_created,
                )
        except HttpError:
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
            user_info: UserInfo = await self._execute_request(user.getInfo)

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
            ) = await self._execute_request(self._session_manager.newSession)

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
        except CertificateVerificationError:
            self._logger.exception("Authentication Error")
            raise
        except HttpError as e:
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

            await self._execute_request(self._session_manager.closeCurrentSession, reason)
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
            async with self._get_lock(self._AUTH_LOCK):
                self._agent.set_auth_token(self._session_token)

                session_details: Session = await self._execute_request(self._session_manager.getCurrentSession)

                return await self._close_session(
                    session_details,
                    SessionManager.CloseReason.CLOSE_REASON_LOGOUT,  # pyright: ignore[reportAttributeAccessIssue]
                )
        except rpc.HttpException:
            self._logger.debug("Session expired before close request", exc_info=True)
        finally:
            self._clear_session_data()

        return True

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

    async def update_sensor_readings_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        """Update sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(device, device.updatable_sensors, SensorUpdate.READINGS)

        return device

    async def update_sensor_readings_for_devices[Device: "RaritanDevice"](
        self, pdu: RaritanPdu, devices: list[Device]
    ) -> list[Device]:
        """Update sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(
            pdu,
            list(flatten([device.updatable_sensors for device in devices])),
            SensorUpdate.READINGS,
        )

        return devices

    async def update_all_sensor_readings_for_device[Device: "RaritanDevice"](self, device: Device) -> Device:
        """Update all sensor readings for device."""
        await self.authenticate()

        await self._update_sensors_for_device(device, device.all_updatable_sensors, SensorUpdate.READINGS)

        return device

    async def update_sensor_readings_for_pdu(self, pdu: RaritanPdu) -> RaritanPdu:
        """Update all sensor readings for PDU."""
        return await self.update_all_sensor_readings_for_device(pdu)

    async def set_outlet_power_state(self, outlet: RaritanPduOutlet, state: OutletPowerState) -> OutletPowerState:
        """Get the power state for a specific Raritan PDU outlet."""
        await self.authenticate()

        try:
            proxy = Outlet(outlet.rid, self._agent)

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
