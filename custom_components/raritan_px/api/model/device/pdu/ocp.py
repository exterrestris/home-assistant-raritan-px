"""Raritan PDU API PDU OCP models."""

from dataclasses import dataclass

from custom_components.raritan_px.api.model.device import RaritanEnergyDevice


@dataclass(kw_only=True)
class RaritanPduOverCurrentProtector(RaritanEnergyDevice):
    """Representation of a Raritan PDU OCP."""

    @property
    def device_type(self) -> str:
        """Return the type of this device."""
        return "Overcurrent Protector"
