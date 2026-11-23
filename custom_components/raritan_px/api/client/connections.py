"""API connection management for API client."""

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from raritan import rpc
from raritan.rpc.session import SessionManager

from custom_components.raritan_px.utils import LockManager, Manager

if TYPE_CHECKING:
    from asyncio import Lock
    from datetime import datetime

    from custom_components.raritan_px.api.client.struct import ConnectionDetails

_LOGGER = logging.getLogger(__name__)


class Connection:
    """API connection."""

    _agent: rpc.Agent
    _lock: Lock
    _config: ConnectionDetails
    _session_manager: SessionManager | None = None
    session_token: str | None = None
    session_created: datetime | None = None

    def __init__(
        self,
        *,
        config: ConnectionDetails,
        lock: Lock,
    ) -> None:
        """Initialise the connection manager."""
        super().__init__()

        self._config = config
        self._lock = lock
        self._agent = rpc.Agent(
            self._config.protocol,
            f"{self._config.host}:{self._config.port}",
            disable_certificate_verification=not self._config.verify_ssl,
            timeout=self._config.timeout,
        )

    @property
    def agent(self) -> rpc.Agent:
        """Get the RPC agent for this connection."""
        return self._agent

    @property
    def lock(self) -> Lock:
        """Get the lock for this connection."""
        return self._lock

    @property
    def config(self) -> ConnectionDetails:
        """Get the config for this connection."""
        return self._config

    @property
    def session_manager(self) -> SessionManager:
        """Get the session manager for this connection."""
        if not self._session_manager:
            self._session_manager = self.proxy(SessionManager, "/session")

        return self._session_manager

    def proxy[T: "rpc.Interface"](self, interface: type[T], target: str) -> T:
        """Create an RPC proxy using the agent of this connection."""
        return interface(target, self.agent)

    def set_auth_from_credentials(self) -> None:
        """Use credentials to authenticate this connection."""
        if self._config.auth is None:
            message: str = f"No authentication information provided for {self._config.host}"
            raise ValueError(message)

        self.agent.set_auth_basic(self._config.auth.user, self._config.auth.passwd)

    def set_auth_from_token(self) -> None:
        """Use session token to authenticate this connection."""
        self.agent.set_auth_token(self.session_token)

    def clear_session_data(self) -> None:
        """Clear session data for this connection."""
        self.session_token = None
        self.session_created = None


class ConnectionManager(Manager[Connection]):
    """API connection manager."""

    _locks: LockManager
    _config: ConnectionDetails
    _namespace_locks: bool

    def __init__(
        self,
        *,
        config: ConnectionDetails,
        lock_manager: LockManager | None = None,
        logger: logging.Logger | None = None,
        namespace_locks: bool = True,
    ) -> None:
        """Initialise the connection manager."""
        super().__init__()

        self._config = config
        self._locks = lock_manager or LockManager()
        self._logger = logger or _LOGGER
        self._namespace_locks = namespace_locks

    def _create(self, name: str, *, timeout: float | None = None) -> Connection:
        lock_name: str = f"__{name}__REQUESTS" if self._namespace_locks else name

        config = self._config

        if timeout is not None:
            config = replace(self._config, timeout=timeout)

        return Connection(config=config, lock=self._locks.get(lock_name))

    def get(self, name: str, *, timeout: float | None = None) -> Connection:
        """Create a connection by name and store for later retreival."""
        return super().get(name, timeout=timeout)

    def create(self, name: str, *, timeout: float | None = None) -> Connection:
        """Create a connection by name and store for later retreival."""
        return super().create(name, timeout=timeout)
