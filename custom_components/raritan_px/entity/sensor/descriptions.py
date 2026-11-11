"""Raritan PDU sensor entity descriptions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import DEGREE, EntityCategory, UnitOfEnergy

from custom_components.raritan_px.api.model.network import NetworkInterface, NetworkInterfaceState, NetworkInterfaceType
from custom_components.raritan_px.api.model.sensor.state import (
    NormalAlarmed,
    OkFaulted,
    OpenClosed,
    ResidualCurrentStatus,
)
from custom_components.raritan_px.entity.descriptions import (
    RaritanDeviceEntityDescription,
    RaritanPduEntityDescription,
    RaritanPduInletEntityDescription,
    RaritanPduOutletEntityDescription,
    RaritanPduOverCurrentProtectorEntityDescription,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, kw_only=True)
class RaritanDeviceSensorEntityDescription(SensorEntityDescription, RaritanDeviceEntityDescription):
    """Base class for a Raritan PDU device sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduInletSensorEntityDescription(RaritanDeviceSensorEntityDescription, RaritanPduInletEntityDescription):
    """Base class for a Raritan PDU inlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOutletSensorEntityDescription(RaritanDeviceSensorEntityDescription, RaritanPduOutletEntityDescription):
    """Base class for a Raritan PDU outlet sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduSensorEntityDescription(RaritanDeviceSensorEntityDescription, RaritanPduEntityDescription):
    """Base class for a Raritan PDU sensor entity description."""


@dataclass(frozen=True, kw_only=True)
class RaritanPduOverCurrentProtectorSensorEntityDescription(
    RaritanDeviceSensorEntityDescription, RaritanPduOverCurrentProtectorEntityDescription
):
    """Base class for a Raritan PDU outlet sensor entity description."""


SENSOR_BACKED_SENSOR_DESCRIPTIONS: tuple[RaritanDeviceSensorEntityDescription, ...] = (
    # region PDU sensor-backed sensors
    RaritanPduSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    RaritanPduSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        name="Apparent Energy",
    ),
    # endregion
    # region Outlet sensor-backed sensors
    RaritanPduOutletSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Peak Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="maximum_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Maximum Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="unbalanced_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Current",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="displacement_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        name="Displacement Power Factor",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        name="Apparent Energy",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="phase_angle",
        state_class=SensorStateClass.MEASUREMENT,
        name="Phase Angle",
        native_unit_of_measurement=DEGREE,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="line_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        name="Line Frequency",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="crest_factor",
        state_class=SensorStateClass.MEASUREMENT,
        name="Crest Factor",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="voltage_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="current_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="inrush_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Inrush Current",
    ),
    # endregion
    # region Inlet sensor-backed sensors
    RaritanPduInletSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Peak Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_ac_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual AC Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_dc_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual DC Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="displacement_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        name="Displacement Power Factor",
    ),
    RaritanPduInletSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        name="Apparent Energy",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_line_line_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Line-Line Current",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Voltage",
    ),
    RaritanPduInletSensorEntityDescription(
        key="unbalanced_line_line_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Unbalanced Line-Line Voltage",
    ),
    RaritanPduInletSensorEntityDescription(
        key="line_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduInletSensorEntityDescription(
        key="phase_angle",
        state_class=SensorStateClass.MEASUREMENT,
        name="Phase Angle",
        native_unit_of_measurement=DEGREE,
    ),
    RaritanPduInletSensorEntityDescription(
        key="crest_factor",
        state_class=SensorStateClass.MEASUREMENT,
        name="Crest Factor",
    ),
    RaritanPduInletSensorEntityDescription(
        key="voltage_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduInletSensorEntityDescription(
        key="current_total_harmonic_distortion",
        state_class=SensorStateClass.MEASUREMENT,
        name="Voltage Total Harmonic Distortion",
    ),
    RaritanPduInletSensorEntityDescription(
        key="power_quality",
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        name="Power_Quality",
    ),
    RaritanPduInletSensorEntityDescription(
        key="surge_protector_status",
        device_class=SensorDeviceClass.ENUM,
        options=OkFaulted.options(),
        name="Surge Protector Status",
    ),
    RaritanPduInletSensorEntityDescription(
        key="residual_current_status",
        device_class=SensorDeviceClass.ENUM,
        options=ResidualCurrentStatus.options(),
        name="Residual Current Status",
    ),
    # endregion
    # region Overcurrent Protector Sensors
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="trip",
        device_class=SensorDeviceClass.ENUM,
        options=OpenClosed.options(),
        name="Trip Status",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Peak Current",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="maximum_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Maximum Current",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="active_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="displacement_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        name="Displacement Power Factor",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="crest_factor",
        state_class=SensorStateClass.MEASUREMENT,
        name="Crest Factor",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="active_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        name="Apparent Energy",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="phase_angle",
        state_class=SensorStateClass.MEASUREMENT,
        name="Phase Angle",
        native_unit_of_measurement=DEGREE,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="line_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="residual_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual Current",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="residual_ac_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual AC Current",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="residual_dc_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        name="Residual DC Current",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="residual_current_status",
        device_class=SensorDeviceClass.ENUM,
        options=ResidualCurrentStatus.options(),
        name="Residual Current Status",
    ),
    # endregion
)
SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP = {(type(desc), desc.key): desc for desc in SENSOR_BACKED_SENSOR_DESCRIPTIONS}

SENSOR_BACKED_MULTI_SENSOR_DESCRIPTIONS_MAP: dict[
    tuple[type, str], Callable[[str, int], RaritanDeviceSensorEntityDescription]
] = {
    (RaritanPduSensorEntityDescription, "power_supply_status"): lambda key, idx: RaritanPduSensorEntityDescription(
        key=key,
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        translation_key="pdu_power_supply_status",
        translation_placeholders={"idx": str(idx + 1)},
    ),
}


PDU_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduSensorEntityDescription, ...] = (
    RaritanPduSensorEntityDescription(
        key="voltage_rating",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_voltage_rating",
        entity_registry_enabled_default=False,
    ),
    RaritanPduSensorEntityDescription(
        key="current_rating",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_current_rating",
        entity_registry_enabled_default=False,
    ),
    RaritanPduSensorEntityDescription(
        key="frequency_rating",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_frequency_rating",
        entity_registry_enabled_default=False,
    ),
    RaritanPduSensorEntityDescription(
        key="power_rating",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="pdu_power_rating",
        entity_registry_enabled_default=False,
    ),
)

PDU_NETWORK_ENTITY_DESCRIPTIONS: tuple[Callable[[str, NetworkInterface], RaritanPduSensorEntityDescription], ...] = (
    lambda key, interface: RaritanPduSensorEntityDescription(
        key=f"network_interfaces[{key}].state",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=NetworkInterfaceState.options(),
        translation_key=f"pdu_network_{interface.type.name.lower()}_state",
        translation_placeholders={"if_name": interface.label},
        entity_registry_enabled_default=(interface.type == NetworkInterfaceType.ETHERNET),
    ),
)

OUTLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduOutletSensorEntityDescription, ...] = (
    RaritanPduOutletSensorEntityDescription(
        key="label",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="outlet_label",
    ),
    RaritanPduOutletSensorEntityDescription(
        key="receptacle_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="outlet_receptacle_type",
        entity_registry_enabled_default=False,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="inlet.short_device_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="outlet_inlet",
        is_available_for=lambda x: x.inlet is not None,
    ),
    RaritanPduOutletSensorEntityDescription(
        key="ocp.short_device_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="outlet_ocp",
        is_available_for=lambda x: x.ocp is not None,
    ),
)

INLET_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduInletSensorEntityDescription, ...] = (
    RaritanPduInletSensorEntityDescription(
        key="label",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="inlet_label",
    ),
    RaritanPduInletSensorEntityDescription(
        key="plug_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="inlet_plug_type",
        entity_registry_enabled_default=False,
    ),
)

OVERCURRENT_PROTECTOR_ATTRIBUTE_BACKED_ENTITY_DESCRIPTIONS: tuple[
    RaritanPduOverCurrentProtectorSensorEntityDescription, ...
] = (
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="label",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="ocp_label",
    ),
    RaritanPduOverCurrentProtectorSensorEntityDescription(
        key="inlet.short_device_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="ocp_inlet",
        is_available_for=lambda x: x.inlet is not None,
    ),
)


def get_entity_description[SensorDesc: "RaritanDeviceSensorEntityDescription"](
    desc_type: type[SensorDesc], sensor_name: str
) -> SensorDesc | None:
    """Get the entity description instance matching the sensor type and name."""
    if (desc_type, sensor_name) in SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP[(desc_type, sensor_name)]  # pyright: ignore[reportReturnType, reportArgumentType]

    if ":" in sensor_name:
        generic_name, idx = sensor_name.split(":")

        if (desc_type, generic_name) in SENSOR_BACKED_MULTI_SENSOR_DESCRIPTIONS_MAP:
            return SENSOR_BACKED_MULTI_SENSOR_DESCRIPTIONS_MAP[(desc_type, generic_name)](sensor_name, int(idx))  # pyright: ignore[reportReturnType, reportArgumentType]

    return None
