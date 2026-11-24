"""Firmware catalogue models."""

from __future__ import annotations

from enum import StrEnum, unique

from packaging.version import Version
from pydantic import BaseModel, Field, HttpUrl

# Used for parsing by Pydantic so cannot be in a type checking block
from custom_components.raritan_px.firmware.model.types import Version as VersionType  # noqa: TC001
from custom_components.raritan_px.utils import normalise_version


@unique
class Product(StrEnum):
    """Product familes."""

    PX2 = "PX2"
    PX3 = "PX3"
    PXC = "PXC"
    PXO = "PXO"

    @staticmethod
    def from_model(model: str) -> Product:
        """Get the product from the specifed model string."""
        return Product(model[:3].upper())

    @staticmethod
    def supported_model(model: str) -> bool:
        """Check if the model is a supported product."""
        try:
            Product.from_model(model)
        except ValueError:
            return False
        else:
            return True


class Firmware(BaseModel):
    """Firmware."""

    version: VersionType
    firmware_url: HttpUrl
    products: list[Product] = Field(..., min_length=1)
    support_url: HttpUrl | None = None
    release_notes_url: HttpUrl | None = None
    min_prev_version: VersionType | None = None
    unsupported_models: list[str] | None = Field(None, min_length=1)

    def supports(self, device: Product | str, version: str | Version | None = None) -> bool:
        """Check if this firmware supports the specified device, with optional additional version check."""
        if not isinstance(device, Product):
            if self.unsupported_models and device not in self.unsupported_models:
                return False

            product = Product.from_model(device)
        else:
            product = device

        return product in self.products and (version is None or self.can_upgrade_from(version))

    def is_newer_than(self, version: str | Version) -> bool:
        """Check if this firmware is newer than the specified version."""
        return self.normalise(version) < self.version

    def can_upgrade_from(self, version: str | Version) -> bool:
        """Check if this firmware can upgrade from the specified version."""
        if self.is_newer_than(version):
            return self.min_prev_version is None or self.normalise(version) >= self.min_prev_version

        return False

    @staticmethod
    def normalise(version: str | Version) -> Version:
        """Strip build information from version string."""
        return normalise_version(version)


class Advisory(BaseModel):
    """Firmware Advisory."""

    issue: str
    description: str | None = None
    affects: list[str] = Field(..., min_length=1)
    fixed_in: str | None = None


class FirmwareCatalogue(BaseModel):
    """Firmware Catalogue."""

    version: VersionType
    products: list[Product] | None = Field(None, min_length=1)
    firmwares: list[Firmware] = Field(..., description="", min_length=1)
    advisories: list[Advisory] | None = Field(None, min_length=1)

    def get_available_firmware(
        self,
        model: str,
        *,
        current_firmware: str | Version | None = None,
        include_current: bool = True,
    ) -> list[Firmware]:
        """Get all firmwares for the specified model that support upgrading from the specified version."""
        if not self.supports_model(model):
            return []

        firmwares = [firmware for firmware in self.firmwares if firmware.supports(model)]
        firmwares.sort(key=lambda firmware: firmware.version, reverse=True)

        if current_firmware:
            min_version = Firmware.normalise(current_firmware)

            firmwares = [
                firmware
                for firmware in firmwares
                if firmware.can_upgrade_from(min_version) or (include_current and min_version == firmware.version)
            ]

        return firmwares

    def get_latest_firmware(
        self,
        model: str,
        *,
        current_firmware: str | Version | None = None,
        include_current: bool = True,
    ) -> Firmware | None:
        """Get the latest firmware for the specified model that supports upgrading from the specified version."""
        firmwares = self.get_available_firmware(
            model, current_firmware=current_firmware, include_current=include_current
        )

        return next(iter(firmwares), None)

    def get_firmware(self, version: str, model: str) -> Firmware | None:
        """Get a specfic firmware for the specified model."""
        desired = Firmware.normalise(version)

        for firmware in self.get_available_firmware(model):
            if desired == Firmware.normalise(firmware.version):
                return firmware

        return None

    def is_out_of_date(self, latest: str) -> bool:
        """Check if the catalogue is older than the specified version."""
        return Version(latest) > self.version

    def supports_model(self, model: str) -> bool:
        """Check if the catalogue can provide firmware for the specified model."""
        try:
            return self.supports_product(Product.from_model(model))
        except ValueError:
            return False

    def supports_product(self, product: Product) -> bool:
        """Check if the catalogue can provide firmware for the specified model."""
        return product in self.products if self.products else True

    @staticmethod
    def normalise(version: str | Version) -> Version:
        """Strip build information from version string."""
        return normalise_version(version, segments=4)
