from .model.device.states import OutletPowerState, RaritanState

from raritan.rpc import Enumeration as RpcEnumeration
from raritan.rpc.pdumodel import Outlet

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
