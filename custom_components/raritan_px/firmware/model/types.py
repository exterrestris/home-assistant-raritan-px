"""Firmware catalogue Pydantic types."""

from typing import TYPE_CHECKING, Annotated, Any

import packaging.version
from pydantic_core import core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue


class _VersionPydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        def validate_version(value: Any) -> packaging.version.Version:
            if isinstance(value, packaging.version.Version):
                return value

            if isinstance(value, str):
                try:
                    return packaging.version.Version(value)
                except packaging.version.InvalidVersion as exc:
                    msg = f"Invalid version string: {value!r}"
                    raise ValueError(msg) from exc

            msg_0 = "Expected a version string or Version instance"
            raise ValueError(msg_0)

        return core_schema.no_info_after_validator_function(
            validate_version,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(packaging.version.Version),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str, return_schema=core_schema.str_schema()),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_obj: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "pep440-version"}


Version = Annotated[packaging.version.Version, _VersionPydanticAnnotation]
