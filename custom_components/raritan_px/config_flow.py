"""Config flow for Raritan PX2/PX3 PDU."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any, Self

import voluptuous as vol

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
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import callback

from . import (
    get_credentials,
    set_credentials,
)
from .const import (
    CONF_CONFIG_ENTRY_MINOR_VERSION,
    DOMAIN,
)

from .api import (
    RaritanClient,
    AuthenticationDetails,
    ConnectionDetails,
    AuthenticationError,
    RaritanClientError,
    RaritanPdu,
)


_LOGGER = logging.getLogger(__name__)

STEP_AUTH_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)

STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class RaritanPduConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RaritanPdu."""

    VERSION = 1
    MINOR_VERSION = CONF_CONFIG_ENTRY_MINOR_VERSION

    host: str | None = None
    port: int | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""

    @callback
    def _get_config_updates(
        self, entry: ConfigEntry, host: str, credentials: AuthenticationDetails | None, device: RaritanPdu | None
    ) -> dict | None:
        """Return updates if the host or device config has changed."""
        entry_data = entry.data
        updates: dict[str, Any] = {}
        new_connection_params = False
        if entry_data[CONF_HOST] != host:
            updates[CONF_HOST] = host
        if device and credentials:
            existing: AuthenticationDetails | None = None

            if CONF_USERNAME in entry.data and CONF_PASSWORD in entry.data:
                existing = AuthenticationDetails(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

            if credentials != existing:
                updates[CONF_USERNAME] = credentials.user
                updates[CONF_PASSWORD] = credentials.passwd

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
    def _async_get_host_port(host_str: str) -> tuple[str, int | None]:
        """Parse the host string for host and port."""
        host, _, port_str = host_str.partition(":")

        if not port_str:
            return host, None

        try:
            port = int(port_str)
        except ValueError:
            return host, None

        return host, port

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            if not (host := user_input[CONF_HOST]):
                pass

            host, port = self._async_get_host_port(host)

            match_dict: dict[str, Any] = {CONF_HOST: host}
            if port:
                self.port = port
                match_dict[CONF_PORT] = port
            self._async_abort_entries_match(match_dict)

            self.host = host
            credentials = await get_credentials(self.hass)
            try:
                device = await self._async_try_connect_all(
                    host,
                    credentials=credentials,
                    raise_on_progress=False,
                    port=port,
                )
            except AuthenticationError:
                return await self.async_step_user_auth_confirm()
            except RaritanClientError as ex:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(ex)
            else:
                if not device:
                    return await self.async_step_user_auth_confirm()

                return self._async_create_or_update_entry_from_device(device, credentials)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_HOST, default=""): str}),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_user_auth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that auth is required."""
        errors: dict[str, str] = {}
        if TYPE_CHECKING:
            # self.host is set by async_step_user and async_step_pick_device
            assert self.host is not None
        placeholders: dict[str, str] = {CONF_HOST: self.host}

        if user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            credentials = AuthenticationDetails(username, password)
            device: RaritanPdu | None
            try:
                device = await self._async_try_connect_all(
                    self.host,
                    credentials=credentials,
                    raise_on_progress=False,
                    port=self.port,
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
                    await set_credentials(self.hass, credentials)
                    self.hass.async_create_task(
                        self._async_reload_requires_auth_entries(), eager_start=False
                    )

                    return self._async_create_or_update_entry_from_device(device, credentials)

        return self.async_show_form(
            step_id="user_auth_confirm",
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _async_reload_requires_auth_entries(self) -> None:
        """Reload all config entries after auth update."""
        _config_entries = self.hass.config_entries

        if self.source == SOURCE_REAUTH:
            await _config_entries.async_reload(self._get_reauth_entry().entry_id)

        for flow in _config_entries.flow.async_progress_by_handler(
            DOMAIN, include_uninitialized=True
        ):
            context = flow["context"]
            if context.get("source") != SOURCE_REAUTH:
                continue
            entry_id = context["entry_id"]
            if entry := _config_entries.async_get_entry(entry_id):
                await _config_entries.async_reload(entry.entry_id)

    @callback
    def _async_create_or_update_entry_from_device(
        self, device: RaritanPdu, credentials: AuthenticationDetails | None = None
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

        if (credentials):
            data[CONF_USERNAME] = credentials.user
            data[CONF_PASSWORD] = credentials.passwd

        if not entry:
            return self.async_create_entry(
                title=f"{device.name} {device.model}",
                data=data,
            )

        return self.async_update_reload_and_abort(entry, data=data)

    async def _async_try_connect_all(
        self,
        host: str,
        credentials: AuthenticationDetails | None,
        raise_on_progress: bool,
        *,
        port: int | None = None,
    ) -> RaritanPdu | None:
        """Try to connect to the device speculatively."""
        if credentials:
            client = RaritanClient(
                self.hass, ConnectionDetails(host=host, auth=credentials)
            )

            pdu = await client.get_pdu_info(update_sensor_data=False)
        else:
            return None

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
        entry_data = reauth_entry.data
        host = entry_data[CONF_HOST]
        port = entry_data.get(CONF_PORT)

        if user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            credentials = AuthenticationDetails(username, password)
            try:
                device = await self._async_try_connect_all(
                    host,
                    credentials=credentials,
                    raise_on_progress=False,
                    port=port,
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
                    await set_credentials(self.hass, credentials)
                    if updates := self._get_config_updates(reauth_entry, host, credentials, device):
                        self.hass.config_entries.async_update_entry(
                            reauth_entry, data=updates
                        )
                    self.hass.async_create_task(
                        self._async_reload_requires_auth_entries(), eager_start=False
                    )
                    return self.async_abort(reason="reauth_successful")

        # Old config entries will not have these values.
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

        host = reconfigure_entry.data[CONF_HOST]
        port = reconfigure_entry.data.get(CONF_PORT)

        if user_input is not None:
            host, port = self._async_get_host_port(host)

            self.host = host
            credentials = await get_credentials(self.hass)
            try:
                device = await self._async_try_connect_all(
                    host,
                    credentials=credentials,
                    raise_on_progress=False,
                    port=port,
                )
            except AuthenticationError:  # Error from the update()
                return await self.async_step_user_auth_confirm()
            except RaritanClientError as ex:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(ex)
            else:
                if not device:
                    return await self.async_step_user_auth_confirm()

                return self._async_create_or_update_entry_from_device(device)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_DATA_SCHEMA,
                {CONF_HOST: f"{host}:{port}" if port else host},
            ),
            errors=errors,
            description_placeholders={
                **placeholders,
            },
        )

