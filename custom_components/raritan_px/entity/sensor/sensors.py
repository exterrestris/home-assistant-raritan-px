
from dataclasses import asdict
from typing import TypeVar

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, DEGREE

from custom_components.raritan_px.api.model.sensor import RaritanSensor
from custom_components.raritan_px.entity.sensor.description import RaritanPduSensorEntityDescription
from custom_components.raritan_px.api.model.sensor.states import NormalAlarmed, OkFaulted, ResidualCurrentStatus
from custom_components.raritan_px.entity.sensor.description import (
    RaritanPduDeviceSensorEntityDescription,
    RaritanPduInletSensorEntityDescription,
    RaritanPduOutletSensorEntityDescription,
)


SENSOR_BACKED_SENSOR_DESCRIPTIONS: tuple[RaritanPduDeviceSensorEntityDescription, ...] = (
    #region PDU sensor-backed sensors
    RaritanPduSensorEntityDescription(
        key="power_supply_status",
        device_class=SensorDeviceClass.ENUM,
        options=NormalAlarmed.options(),
        name="Power Supply {} Status"
    ),
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
    ),
    RaritanPduSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        name="Apparent Energy",
    ),
    #endregion
    #region Outlet sensor-backed sensors
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
    ),
    RaritanPduOutletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
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
    #endregion
    #region Inlet sensor-backed sensors
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
    ),
    RaritanPduInletSensorEntityDescription(
        key="apparent_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
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
        key="residual current status",
        device_class=SensorDeviceClass.ENUM,
        options=ResidualCurrentStatus.options(),
        name="Residual Current Status",
    ),
    #endregion
)
SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP = { (type(desc), desc.key) : desc for desc in SENSOR_BACKED_SENSOR_DESCRIPTIONS}

OUTLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduOutletSensorEntityDescription, ...] = (
    RaritanPduOutletSensorEntityDescription(
        key="outlet_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        convert_fn=lambda idx: idx + 1,
        name="Outlet",
    ),
)

INLET_PROPERTY_BACKED_ENTITY_DESCRIPTIONS: tuple[RaritanPduInletSensorEntityDescription, ...] = (
    RaritanPduInletSensorEntityDescription(
        key="inlet_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        convert_fn=lambda idx: idx + 1,
        name="Inlet",
    ),
)

T = TypeVar('T', bound="RaritanPduDeviceSensorEntityDescription", covariant=True)

def get_entity_description(desc_type: type[T], sensor_name: str, sensor: RaritanSensor) -> T:
    def default_name(name: str = sensor_name) -> str:
        return name.replace('_', ' ').replace(':', ' ').title()

    if (desc_type, sensor_name) in SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP:
        return SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP[(desc_type, sensor_name)] # pyright: ignore[reportReturnType, reportArgumentType]

    if ':' in sensor_name:
        generic_name, idx = sensor_name.split(':')

        if (desc_type, generic_name) in SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP:
            desc = SENSOR_BACKED_SENSOR_DESCRIPTIONS_MAP[(desc_type, generic_name)] # pyright: ignore[reportArgumentType]

            def formatted_name():
                if type(desc.name) is str:
                    return desc.name.format(int(idx) + 1)

                return f"{default_name(generic_name)} {int(idx) + 1}"

            return desc_type(
                **(asdict(desc) | {
                    'key': sensor_name,
                    'name': formatted_name(),
                })
            )

    return desc_type(
        key = sensor_name,
        name = default_name(),
    )
