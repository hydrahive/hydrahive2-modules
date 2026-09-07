from __future__ import annotations

import pytest

from backend.adapter import AdapterUnavailable, OpenTorAdapter
from backend.policy import PolicyError, redact_text, validate_fetch_url, validate_redirect


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/file",
    "http://127.0.0.1:8080/admin",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data",
    "http://user:pass@example.com/",
])
def test_blocks_unsafe_fetch_urls(url):
    with pytest.raises(PolicyError):
        validate_fetch_url(url)


def test_allows_public_and_onion_urls():
    assert validate_fetch_url("https://example.org/report") == "https://example.org/report"
    assert validate_fetch_url("http://abcdefghijklmnop.onion/") == "http://abcdefghijklmnop.onion/"


def test_blocks_onion_redirect_to_clearnet():
    with pytest.raises(PolicyError):
        validate_redirect("http://abcdefghijklmnop.onion/", "https://example.org/")


def test_redacts_personal_contact_data():
    value = redact_text("mail a.person@example.org or call +49 123 456789", 8000)
    assert "a.person@example.org" not in value
    assert "+49 123 456789" not in value


def test_adapter_fails_closed_without_server_configured_root(tmp_path):
    with pytest.raises(AdapterUnavailable, match="opentor_unavailable"):
        OpenTorAdapter(str(tmp_path)).status()
