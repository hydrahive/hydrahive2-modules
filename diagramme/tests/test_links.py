"""Signierte Ansichts-Adresse (Spec §4a): HMAC, Zweck-Schlüssel, 10 min, zeitkonstant."""
from __future__ import annotations

import hmac

import pytest
from backend import links


def test_sign_and_check_roundtrip():
    exp, sig = links.sign("d_abc", now=1000)
    assert exp == 1000 + links.TTL_SECONDS == 1600
    assert links.check("d_abc", exp, sig, now=1000)
    assert links.check("d_abc", exp, sig, now=1599)


def test_expired_link_is_invalid():
    exp, sig = links.sign("d_abc", now=1000)
    assert not links.check("d_abc", exp, sig, now=1600)
    assert not links.check("d_abc", exp, sig, now=99999)


@pytest.mark.parametrize("change", ["id", "exp", "sig"])
def test_tampered_link_is_invalid(change):
    exp, sig = links.sign("d_abc", now=1000)
    vid, e, s = "d_abc", exp, sig
    if change == "id":
        vid = "d_abd"
    elif change == "exp":
        e = exp + 1
    else:
        s = ("0" if sig[0] != "0" else "1") + sig[1:]
    assert not links.check(vid, e, s, now=1000)


def test_link_far_in_the_future_is_invalid():
    """Eine selbst gebaute Adresse mit langer Laufzeit hilft nicht – exp höchstens TTL voraus."""
    exp = 1000 + 10 * links.TTL_SECONDS
    sig = links._mac(f"diagramme|view|d_abc|{exp}")
    assert not links.check("d_abc", exp, sig, now=1000)


@pytest.mark.parametrize("sig", ["", "zz", None, 5, "a" * 200])
def test_garbage_signature_is_invalid(sig):
    exp, _ = links.sign("d_abc", now=1000)
    assert not links.check("d_abc", exp, sig, now=1000)


def test_key_is_derived_not_the_secret_itself():
    from hydrahive.settings import settings
    assert links._key() != settings.secret_key.encode()
    assert len(links._key()) == 32


def test_comparison_is_constant_time(monkeypatch):
    used = []
    real = hmac.compare_digest

    def spy(a, b):
        used.append(True)
        return real(a, b)

    monkeypatch.setattr(links.hmac, "compare_digest", spy)
    exp, sig = links.sign("d_abc", now=1000)
    links.check("d_abc", exp, sig, now=1000)
    assert used


def test_url_has_no_token_and_points_to_sandbox():
    url = links.view_url("d_abc", now=1000)
    assert url.startswith("/api/module-device/diagramme/sandbox/d_abc?exp=1600&sig=")
    assert "token" not in url
