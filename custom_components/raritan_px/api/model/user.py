"""Raritan PDU user models."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Self

from custom_components.raritan_px.api import RaritanEnum
from custom_components.raritan_px.api.model import RaritanModel

if TYPE_CHECKING:
    from raritan.rpc import usermgmt


@dataclass(kw_only=True)
class RaritanUser(RaritanModel):
    """Representation of a Raritan PDU user."""

    fullname: str
    email: str
    _privileges: list[RaritanUserPrivilege]

    @classmethod
    def from_rpc(cls, info: usermgmt.UserInfo, privileges: list[usermgmt.Role.Privilege]) -> Self:
        """Create from RPC API repsonse."""
        return cls(
            fullname=info.auxInfo.fullname,
            email=info.auxInfo.eMail,
            _privileges=[RaritanUserPrivilege.from_rpc(privilege) for privilege in privileges],
        )

    def has(self, privilege: Privilege) -> bool:
        """Determine if user has a particular privilege."""
        return any(user_privilege.privilege == privilege for user_privilege in self._privileges)

    def can(self, privilege: Privilege) -> bool:
        """Determine if user can use particular privilege."""
        return bool(self.has(privilege) or self.has(Privilege.ADMIN_PRIVILEGE))

    @property
    def privileges(self) -> list[RaritanUserPrivilege]:
        """Get the privileges for this user."""
        return [privilege for privilege in self._privileges if isinstance(privilege.privilege, Privilege)]

    @property
    def unknown_privileges(self) -> list[RaritanUserPrivilege]:
        """Get the privileges for this user."""
        return [privilege for privilege in self._privileges if not isinstance(privilege.privilege, Privilege)]


@dataclass(kw_only=True)
class RaritanUserPrivilege(RaritanModel):
    """Representation of a Raritan PDU user privilege."""

    privilege: Privilege | str | None

    @classmethod
    def from_rpc(cls, priv: usermgmt.Role.Privilege) -> Self:
        """Create from RPC API repsonse."""
        try:
            privilege = Privilege(priv.name)
        except ValueError:
            privilege = priv.name

        return cls(privilege=privilege)

    def __str__(self) -> str:
        """Get string representation of user privilege."""
        return str(self.privilege)


class Privilege(RaritanEnum, StrEnum):
    """Network interface type enum."""

    ACKNOWLEDGE_ALARMS = "acknowledgeAlarms"
    ADMIN_PRIVILEGE = "adminPrivilege"
    CHANGE_ASSET_STRIP_CONFIGURATION = "changeAssetStripConfiguration"
    CHANGE_AUTH_SETTINGS = "changeAuthSettings"
    CHANGE_DATE_TIME_SETTINGS = "changeDateTimeSettings"
    CHANGE_DOOR_ACCESS_RULES = "changeDoorAccessRules"
    CHANGE_EXTERNAL_SENSORS_CONFIGURATION = "changeExternalSensorsConfiguration"
    CHANGE_MODEM_CONFIGURATION = "changeModemConfiguration"
    CHANGE_NETWORK_SETTINGS = "changeNetworkSettings"
    CHANGE_PASSWORD = "changePassword"  # noqa: S105
    CHANGE_PDU_CONFIGURATION = "changePduConfiguration"
    CHANGE_REDFISH_SETTINGS = "changeRedfishSettings"
    CHANGE_SECURITY_SETTINGS = "changeSecuritySettings"
    CHANGE_SNMP_SETTINGS = "changeSnmpSettings"
    CHANGE_SX_PORT_SETTINGS = "changeSxPortSettings"
    CHANGE_USER_SETTINGS = "changeUserSettings"
    CHANGE_WEBCAM_SETTINGS = "changeWebcamSettings"
    CLEAR_LOG = "clearLog"
    FIRMWARE_UPDATE = "firmwareUpdate"
    PERFORM_RESET = "performReset"
    READ_SX_PORT = "readSxPort"
    SWITCH_ACTUATOR = "switchActuator"
    SWITCH_OUTLET = "switchOutlet"
    SWITCH_OUTLET_GROUP = "switchOutletGroup"
    VIEW_AUTH_SETTINGS = "viewAuthSettings"
    VIEW_DOOR_ACCESS_RULES = "viewDoorAccessRules"
    VIEW_EVENT_SETUP = "viewEventSetup"
    VIEW_EVERYTHING = "viewEverything"
    VIEW_LOG = "viewLog"
    VIEW_SECURITY_SETTINGS = "viewSecuritySettings"
    VIEW_SNMP_SETTINGS = "viewSnmpSettings"
    VIEW_SX_PORT_SETTINGS = "viewSxPortSettings"
    VIEW_USER_SETTINGS = "viewUserSettings"
    VIEW_WEBCAM_SETTINGS = "viewWebcamSettings"
    WRITE_SX_PORT = "writeSxPort"
