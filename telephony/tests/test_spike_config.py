from __future__ import annotations

import stat
from pathlib import Path

import pytest

from spike.config import (
    ProbeTarget,
    SecureBaresipConfig,
    SipCredentials,
    render_account,
)


@pytest.mark.parametrize(
    "registrar",
    [
        "37.202.238.230",
        "8.8.8.8",
        "fritz.box",
        "192.168.3.1\nmodule evil.so",
        "127.0.0.1",
    ],
)
def test_probe_target_rejects_non_lan_or_injectable_registrar(registrar: str) -> None:
    with pytest.raises(ValueError, match="private LAN IPv4"):
        ProbeTarget(registrar=registrar)


def test_probe_target_accepts_private_lan_ipv4() -> None:
    assert ProbeTarget(registrar="192.168.3.1").registrar == "192.168.3.1"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("short", "LongEnoughPassword1"),
        ("phone-user;regint=0", "LongEnoughPassword1"),
        ("phone-user\nmodule evil.so", "LongEnoughPassword1"),
        ("phone-user", "short"),
        ("phone-user", "password;regint=0"),
        ("phone-user", "password\nmodule evil.so"),
    ],
)
def test_credentials_reject_account_parameter_injection(
    username: str, password: str
) -> None:
    with pytest.raises(ValueError):
        SipCredentials(username=username, password=password)


def test_credentials_repr_is_fully_redacted() -> None:
    credentials = SipCredentials(
        username="phone-user-01", password="TopSecretPhonePassword"
    )

    rendered = repr(credentials)

    assert "phone-user-01" not in rendered
    assert "TopSecretPhonePassword" not in rendered
    assert "redacted" in rendered


def test_render_account_uses_udp_g711_and_no_sip_trace() -> None:
    target = ProbeTarget(registrar="192.168.3.1")
    credentials = SipCredentials(
        username="phone-user-01", password="TopSecretPhonePassword"
    )

    account = render_account(target, credentials)

    assert "transport=udp" in account
    assert "audio_codecs=pcma,pcmu" in account
    assert "auth_user=phone-user-01" in account
    assert "auth_pass=TopSecretPhonePassword" in account
    assert "sip_trace" not in account


def test_secure_config_uses_0600_and_removes_secret_files(tmp_path: Path) -> None:
    target = ProbeTarget(registrar="192.168.3.1")
    credentials = SipCredentials(
        username="phone-user-01", password="TopSecretPhonePassword"
    )
    parent = tmp_path / "runtime"
    parent.mkdir(mode=0o700)

    with SecureBaresipConfig(
        target=target,
        credentials=credentials,
        module_dir=Path("/opt/baresip/lib/baresip/modules"),
        temp_parent=parent,
    ) as config_dir:
        account_file = config_dir / "accounts"
        config_file = config_dir / "config"
        assert stat.S_IMODE(account_file.stat().st_mode) == 0o600
        assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
        assert "TopSecretPhonePassword" in account_file.read_text()
        assert "stdio.so" not in config_file.read_text()

    assert list(parent.iterdir()) == []
