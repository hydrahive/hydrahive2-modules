"""Secure, minimal Baresip configuration for the FRITZ!Box spike."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Callable

_RFC1918_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{8,64}\Z")
_PASSWORD_PATTERN = re.compile(r"[A-Za-z0-9._!$%&()*+,\-/:<=>?@^`{|}~]{12,128}\Z")


@dataclass(frozen=True, slots=True)
class ProbeTarget:
    """Private registrar endpoint allowed by the spike harness."""

    registrar: str
    port: int = 5060

    def __post_init__(self) -> None:
        try:
            address = ipaddress.ip_address(self.registrar)
        except ValueError as exc:
            raise ValueError("registrar must be a private LAN IPv4 address") from exc
        if address.version != 4 or not any(
            address in network for network in _RFC1918_NETWORKS
        ):
            raise ValueError("registrar must be a private LAN IPv4 address")
        if not 1 <= self.port <= 65535:
            raise ValueError("registrar port must be between 1 and 65535")


@dataclass(frozen=True, slots=True, repr=False)
class SipCredentials:
    """Ephemeral credentials whose representation never includes either field."""

    username: str = field(repr=False)
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if not _USERNAME_PATTERN.fullmatch(self.username):
            raise ValueError("username must be 8-64 safe characters")
        if not _PASSWORD_PATTERN.fullmatch(self.password):
            raise ValueError("password must be 12-128 safe characters")

    def __repr__(self) -> str:
        return "SipCredentials(<redacted>)"


def render_account(target: ProbeTarget, credentials: SipCredentials) -> str:
    """Render one UDP/G.711 account line for a local FRITZ!Box."""
    return (
        f"<sip:{credentials.username}@{target.registrar}:{target.port};transport=udp>"
        f";auth_user={credentials.username};auth_pass={credentials.password}"
        ";audio_codecs=pcma,pcmu;regint=300;answermode=manual\n"
    )


def render_config(module_dir: Path) -> str:
    """Render the registration-only Baresip configuration."""
    module_dir = _validate_module_dir(module_dir)
    return (
        "sip_transports\t\tudp\n"
        "call_accept\t\tno\n"
        "audio_level\t\tno\n"
        f"module_path\t\t{module_dir}\n"
        "module\t\t\tg711.so\n"
        "module_app\t\taccount.so\n"
        "module_app\t\tserreg.so\n"
    )


def render_incoming_account(target: ProbeTarget, credentials: SipCredentials) -> str:
    """Render a UDP account that advertises its registrar-observed NAT contact."""
    return (
        f"<sip:{credentials.username}@{target.registrar}:{target.port};transport=udp>"
        f";auth_user={credentials.username};auth_pass={credentials.password}"
        ";sipnat=received;audio_codecs=pcma,pcmu;regint=0;answermode=manual"
        ";inreq_allowed=yes;check_origin=yes\n"
    )


def render_incoming_config(module_dir: Path) -> str:
    """Render a one-call, loopback-controlled, sendonly-capable configuration."""
    module_dir = _validate_module_dir(module_dir)
    return (
        "sip_transports\t\tudp\n"
        "sip_trans_def\t\tudp\n"
        "sip_listen\t\t0.0.0.0:5060\n"
        "call_accept\t\tyes\n"
        "call_max_calls\t\t1\n"
        "call_local_timeout\t15\n"
        "rtp_ports\t\t20000-20020\n"
        "audio_level\t\tno\n"
        "audio_source\t\tausine,440\n"
        "ctrl_tcp_listen\t127.0.0.1:4444\n"
        f"module_path\t\t{module_dir}\n"
        "module\t\t\tg711.so\n"
        "module\t\t\tausine.so\n"
        "module_app\t\taccount.so\n"
        "module_app\t\tmenu.so\n"
        "module_app\t\tctrl_tcp.so\n"
    )


def _validate_module_dir(module_dir: Path) -> Path:
    module_dir = module_dir.resolve()
    if any(character.isspace() for character in str(module_dir)):
        raise ValueError("module directory must not contain whitespace")
    return module_dir


class SecureBaresipConfig:
    """Create 0600 Baresip files and destroy them when leaving the context."""

    def __init__(
        self,
        *,
        target: ProbeTarget,
        credentials: SipCredentials,
        module_dir: Path,
        temp_parent: Path | None = None,
        config_renderer: Callable[[Path], str] = render_config,
        account_renderer: Callable[[ProbeTarget, SipCredentials], str] = render_account,
    ) -> None:
        self._target = target
        self._credentials = credentials
        self._module_dir = module_dir
        self._temp_parent = temp_parent
        self._config_renderer = config_renderer
        self._account_renderer = account_renderer
        self._temporary: TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        parent = str(self._temp_parent) if self._temp_parent is not None else None
        self._temporary = TemporaryDirectory(prefix="hh-sip-probe-", dir=parent)
        config_dir = Path(self._temporary.name)
        config_dir.chmod(0o700)
        self._write_secret_file(
            config_dir / "config", self._config_renderer(self._module_dir)
        )
        self._write_secret_file(
            config_dir / "accounts",
            self._account_renderer(self._target, self._credentials),
        )
        self._write_secret_file(config_dir / "contacts", "")
        return config_dir

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    @staticmethod
    def _write_secret_file(path: Path, content: str) -> None:
        path.touch(mode=0o600, exist_ok=False)
        path.chmod(0o600)
        path.write_text(content, encoding="utf-8")


class SecureIncomingBaresipConfig(SecureBaresipConfig):
    """Use Gate-2 renderers while preserving the same tmpfs file boundary."""

    def __init__(
        self,
        *,
        target: ProbeTarget,
        credentials: SipCredentials,
        module_dir: Path,
        temp_parent: Path | None = None,
    ) -> None:
        super().__init__(
            target=target,
            credentials=credentials,
            module_dir=module_dir,
            temp_parent=temp_parent,
            config_renderer=render_incoming_config,
            account_renderer=render_incoming_account,
        )
