"""Raritan API client & data models."""

from enum import Enum


class RaritanEnum(Enum):
    """Generic enum."""

    def friendly_name(self) -> str:
        """Return a formatted 'friendly' name for this enum option."""
        return self.name.replace("_", " ").title()

    @classmethod
    def options(cls) -> list[str]:
        """Return a list of the 'friendly' names for all the possible options."""
        return [opt.friendly_name() for opt in list(cls)]
