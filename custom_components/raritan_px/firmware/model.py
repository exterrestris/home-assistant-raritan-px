"""Firmware catalogue models."""

from __future__ import annotations

from enum import StrEnum

from packaging.version import Version
from pydantic import BaseModel, Field, HttpUrl


class Product(StrEnum):
    """Product familes."""

    PX2 = "PX2"
    PX3 = "PX3"
    PX4 = "PX4"
    PXC = "PXC"
    PXO = "PXO"
    PXE = "PXE"

    @staticmethod
    def from_model(model: str) -> Product:
        """Get the product from the specifed model string."""
        return Product(model[:3].upper())


class Firmware(BaseModel):
    """Firmware."""

    version: str
    firmware_url: HttpUrl
    products: list[Product] = Field(..., min_length=1)
    support_url: HttpUrl | None = None
    release_notes_url: HttpUrl | None = None
    min_prev_version: str | None = None
    unsupported_models: list[str] | None = Field(None, min_length=1)

    def supports(self, device: Product | str, version: str | None = None) -> bool:
        """Check if this firmware supports the specified device, with optional additional version check."""
        product = device if isinstance(device, Product) else Product.from_model(device)

        if product in self.products:
            if version is not None:
                return self.can_upgrade_from(version)

            return True

        return False

    def is_newer_than(self, version: str) -> bool:
        """Check if this firmware is newer than the specified version."""
        return self.normalise(version) < self.normalise(self.version)

    def can_upgrade_from(self, version: str) -> bool:
        """Check if this firmware can upgrade from the specified version."""
        if self.is_newer_than(version):
            return self.min_prev_version is None or self.normalise(version) >= self.normalise(self.min_prev_version)

        return False

    @staticmethod
    def normalise(version: str) -> Version:
        """Strip build information from version string."""
        v = Version(version)
        v = (*v.release, 0, 0, 0)[:3]
        return Version(".".join(map(str, v)))


class Advisory(BaseModel):
    """Firmware Advisory."""

    issue: str
    description: str | None = None
    affects: list[str] = Field(..., min_length=1)
    fixed_in: str | None = None


class FirmwareCatalogue(BaseModel):
    """Firmware Catalogue."""

    version: str
    products: list[Product] | None = Field(None, min_length=1)
    firmwares: list[Firmware] = Field(..., description="", min_length=1)
    advisories: list[Advisory] | None = Field(None, min_length=1)

    def get_available_firmware(self, model: str, current_version: str) -> list[Firmware]:
        """Get the firmwares for a model that support upgrading from the specified version."""
        firmwares = [firmware for firmware in self.firmwares if firmware.supports(model, current_version)]
        firmwares.sort(key=lambda firmware: Version(firmware.version), reverse=True)

        return firmwares

    def get_latest_firmware(self, model: str, current_version: str) -> Firmware | None:
        """Get the latest firmware for a model that supports upgrading from the specified version."""
        firmwares = self.get_available_firmware(model, current_version)

        return next(iter(firmwares), None)

    def is_out_of_date(self, latest: str) -> bool:
        """Check if the catalogue is older than the specified version."""
        return Version(latest) > Version(self.version)
