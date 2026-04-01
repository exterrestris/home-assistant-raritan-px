"""Config flow for Raritan PX2/PX3 PDU."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Mapping
import logging
from typing import Any, Self

import voluptuous as vol

from homeassistant.data_entry_flow import section
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import (
    CONF_ALIAS,
    CONF_HOST,
    CONF_MODEL,
    CONF_OPTIONS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback

from custom_components.raritan_px import (
    get_credentials,
    get_connection_details_from_entry,
    set_credentials,
)
from custom_components.raritan_px.api.model.device import RaritanPdu
from custom_components.raritan_px.api.client import (
    RaritanClient,
    UpdateSensors,
    AuthenticationDetails,
    ConnectionDetails,
    AuthenticationError,
    CertificateVerificationError,
    RaritanClientError,
)
from custom_components.raritan_px.api.const import DEFAULT_PORT
from custom_components.raritan_px.const import (
    CONF_CONFIG_ENTRY_MINOR_VERSION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_AUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_DEVICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Required(CONF_OPTIONS): section(
            vol.Schema(
                {
                    vol.Optional(CONF_SSL, default=True): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            {
                "collapsed": True
            },
        )
    }
)

STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Required(CONF_OPTIONS): section(
            vol.Schema(
                {
                    vol.Optional(CONF_SSL, default=True): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            {
                "collapsed": True
            },
        )
    }
)

class RaritanPduConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RaritanPdu."""

    VERSION = 1
    MINOR_VERSION = CONF_CONFIG_ENTRY_MINOR_VERSION

    config: ConnectionDetails | None = None
    host: str | None = None
    port: int | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""

    @callback
    def _get_config_updates(
        self, entry: ConfigEntry, config: ConnectionDetails, device: RaritanPdu | None
    ) -> dict | None:
        """Return updates if the host or device config has changed."""
        entry_data = entry.data
        updates: dict[str, Any] = {}
        new_connection_params = False

        if entry_data[CONF_HOST] != config.host:
            updates[CONF_HOST] = config.host

        if device and config.auth:
            existing: AuthenticationDetails | None = None

            if CONF_USERNAME in entry.data and CONF_PASSWORD in entry.data:
                existing = AuthenticationDetails(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

            if config.auth != existing:
                updates[CONF_USERNAME] = config.auth.user
                updates[CONF_PASSWORD] = config.auth.passwd

        if not updates:
            return None
        updates = {**entry.data, **updates}

        if new_connection_params:
            pass
        return updates
    def is_matching(self, other_flow: Self) -> bool:
        """Return True if other_flow is matching this flow."""
        return other_flow.host == self.host

    @staticmethod
    def _async_get_host_port(host_str: str) -> tuple[str, int]:
        """Parse the host string for host and port."""
        host, _, port_str = host_str.partition(":")

        if not port_str:
            return host, DEFAULT_PORT

        try:
            port = int(port_str)
        except ValueError:
            return host, DEFAULT_PORT

        return host, port

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            host, port = self._async_get_host_port(user_input[CONF_HOST])

            match_dict: dict[str, Any] = {
                CONF_HOST: host,
                CONF_PORT: port,
            }

            self._async_abort_entries_match(match_dict)

            if CONF_USERNAME in user_input and CONF_PASSWORD in user_input:
                credentials = AuthenticationDetails(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            else:
                credentials = await get_credentials(self.hass)

            if CONF_USERNAME in user_input:
                credentials = replace(credentials, user=user_input[CONF_USERNAME])

            if CONF_PASSWORD in user_input:
                credentials = replace(credentials, passwd=user_input[CONF_PASSWORD])

            self.config = ConnectionDetails(
                host=host,
                auth=credentials,
                port=port,
                use_ssl=user_input[CONF_OPTIONS][CONF_SSL],
                verify_ssl=user_input[CONF_OPTIONS][CONF_VERIFY_SSL],
            )

            try:
                device = await self._async_try_connect(
                    self.config,
                    raise_on_progress=False,
                )
            except AuthenticationError as ex:
                errors[CONF_USERNAME] = "invalid_auth"
                placeholders["error"] = str(ex)
            except CertificateVerificationError:
                errors["base"] = "cannot_connect"
                placeholders["error"] = "Cerificate verification failed"
            except RaritanClientError as ex:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(ex)
            else:
                return self._async_create_or_update_entry_from_device(device, self.config)

        suggested = {
        }

        if user_input is not None:
            suggested = {
                **user_input,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_DEVICE_DATA_SCHEMA,
                suggested,
            ),
            errors=errors,
            description_placeholders={
                **placeholders,
            },
        )

    async def _async_reload_requires_auth_entries(self) -> None:
        """Reload all config entries after auth update."""
        _config_entries = self.hass.config_entries

        if self.source == SOURCE_REAUTH:
            await _config_entries.async_reload(self._get_reauth_entry().entry_id)

        for flow in _config_entries.flow.async_progress_by_handler(
            DOMAIN, include_uninitialized=True
        ):
            context = flow["context"] # pyright: ignore[reportTypedDictNotRequiredAccess]
            if context.get("source") != SOURCE_REAUTH:
                continue
            entry_id = context["entry_id"] # pyright: ignore[reportTypedDictNotRequiredAccess]
            if entry := _config_entries.async_get_entry(entry_id):
                await _config_entries.async_reload(entry.entry_id)

    @callback
    def _async_create_or_update_entry_from_device(
        self,
        device: RaritanPdu,
        config: ConnectionDetails | None = None,
    ) -> ConfigFlowResult:
        """Create a config entry from a smart device."""
        entry = None
        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
        elif self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()

        if not entry:
            self._abort_if_unique_id_configured(updates={CONF_HOST: device.host})

        data: dict[str, Any] = {
            CONF_HOST: device.host,
            CONF_ALIAS: device.name,
            CONF_MODEL: device.model,
        }

        if config:
            if config.auth:
                data[CONF_USERNAME] = config.auth.user
                data[CONF_PASSWORD] = config.auth.passwd

            data[CONF_PORT] = config.port
            data[CONF_SSL] = config.use_ssl
            data[CONF_VERIFY_SSL] = config.verify_ssl

        if not entry:
            return self.async_create_entry(
                title=f"{device.name} {device.model}",
                data=data,
            )

        return self.async_update_reload_and_abort(entry, data=data)

    async def _async_try_connect(
        self,
        config: ConnectionDetails,
        raise_on_progress: bool,
    ) -> RaritanPdu:
        """Try to connect to the device speculatively."""

        client = RaritanClient(self.hass, config)

        pdu = await client.get_pdu_info(update_sensor_data=UpdateSensors.NONE)

        if pdu:
            await self.async_set_unique_id(
                pdu.serial_number,
                raise_on_progress=raise_on_progress,
            )
        return pdu


    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start the reauthentication flow if the device needs updated credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        config = await get_connection_details_from_entry(reauth_entry)
        entry_data = reauth_entry.data
        host = entry_data[CONF_HOST]

        if user_input:
            config = replace(config, auth=AuthenticationDetails(user_input[CONF_USERNAME], user_input[CONF_PASSWORD]))

            try:
                device = await self._async_try_connect(
                    config,
                    raise_on_progress=False,
                )
            except AuthenticationError as ex:
                errors[CONF_PASSWORD] = "invalid_auth"
                placeholders["error"] = str(ex)
            except RaritanClientError as ex:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(ex)
            else:
                if not device:
                    errors["base"] = "cannot_connect"
                    placeholders["error"] = "try_connect_all failed"
                else:
                    await self.async_set_unique_id(
                        device.serial_number,
                        raise_on_progress=False,
                    )
                    await set_credentials(self.hass, config.auth)
                    if updates := self._get_config_updates(reauth_entry, config, device):
                        self.hass.config_entries.async_update_entry(
                            reauth_entry, data=updates
                        )
                    self.hass.async_create_task(
                        self._async_reload_requires_auth_entries(), eager_start=False
                    )
                    return self.async_abort(reason="reauth_successful")

        alias = entry_data.get(CONF_ALIAS) or "unknown"
        model = entry_data.get(CONF_MODEL) or "unknown"

        placeholders.update({"name": alias, "model": model, "host": host})

        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Trigger a reconfiguration flow."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        reconfigure_entry = self._get_reconfigure_entry()
        assert reconfigure_entry.unique_id
        await self.async_set_unique_id(reconfigure_entry.unique_id)

        placeholders[CONF_ALIAS] = reconfigure_entry.data[CONF_ALIAS]

        if user_input is not None:
            host, port = self._async_get_host_port(user_input[CONF_HOST])
            credentials = await get_credentials(self.hass, reconfigure_entry)

            if CONF_USERNAME in user_input:
                credentials = replace(credentials, user=user_input[CONF_USERNAME])

            if CONF_PASSWORD in user_input:
                credentials = replace(credentials, passwd=user_input[CONF_PASSWORD])

            self.config = ConnectionDetails(
                host=host,
                auth=credentials,
                port=port,
                use_ssl=user_input[CONF_OPTIONS][CONF_SSL],
                verify_ssl=user_input[CONF_OPTIONS][CONF_VERIFY_SSL],
            )

            try:
                device = await self._async_try_connect(
                    self.config,
                    raise_on_progress=False,
                )
            except AuthenticationError as ex:  # Error from the update()
                errors[CONF_USERNAME] = "invalid_auth"
                placeholders["error"] = str(ex)
            except CertificateVerificationError:
                errors["base"] = "cannot_connect"
                placeholders["error"] = "Cerificate verification failed"
            except RaritanClientError as ex:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(ex)
            else:
                return self._async_create_or_update_entry_from_device(device, self.config)

        host = reconfigure_entry.data[CONF_HOST]
        port = reconfigure_entry.data.get(CONF_PORT)

        suggested = {
            CONF_HOST: f"{host}:{port}" if port else host,
            CONF_USERNAME: reconfigure_entry.data[CONF_USERNAME],
            CONF_OPTIONS: {
                CONF_SSL: reconfigure_entry.data[CONF_SSL],
                CONF_VERIFY_SSL: reconfigure_entry.data[CONF_VERIFY_SSL],
            }
        }

        if user_input is not None:
            suggested = {
                **suggested,
                **user_input,
            }

        alias = reconfigure_entry.data.get(CONF_ALIAS) or "unknown"
        model = reconfigure_entry.data.get(CONF_MODEL) or "unknown"

        placeholders.update({"name": alias, "model": model, "host": host})

        self.context["title_placeholders"] = placeholders

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_DATA_SCHEMA,
                suggested,
            ),
            errors=errors,
            description_placeholders={
                **placeholders,
            },
        )
