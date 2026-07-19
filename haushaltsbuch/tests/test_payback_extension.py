from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

from conftest import PREFIX
from test_v1_api import _create_household


EXTENSION_DIR = (
    Path(__file__).resolve().parents[1] / "browser-extension" / "payback-bridge"
)


def test_extension_package_requires_auth_and_is_reproducible(
    client, owner_headers, monkeypatch, tmp_path
):
    extension = tmp_path / "payback-bridge"
    extension.mkdir()
    (extension / "manifest.json").write_text('{"manifest_version":3}', encoding="utf-8")
    (extension / "popup.js").write_text("console.log('read only');\n", encoding="utf-8")
    monkeypatch.setattr("backend.payback_extension.EXTENSION_DIR", extension)

    url = f"{PREFIX}/loyalty/payback/bridge/extension-package"
    assert client.get(url).status_code == 401
    _create_household(client, owner_headers)
    first = client.get(url, headers=owner_headers)
    second = client.get(url, headers=owner_headers)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()

    archive = base64.b64decode(first.json()["base64"])
    assert first.json()["sha256"] == hashlib.sha256(archive).hexdigest()
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        assert package.namelist() == ["manifest.json", "popup.js"]
        assert package.read("manifest.json") == b'{"manifest_version":3}'


def test_real_extension_manifest_is_minimal_and_uses_optional_hydrahive_hosts():
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["permissions"] == ["storage"]
    assert manifest["host_permissions"] == ["https://www.payback.de/*"]
    assert set(manifest["optional_host_permissions"]) == {
        "https://*/*",
        "http://localhost/*",
        "http://127.0.0.1/*",
    }
    assert manifest["content_scripts"][0]["matches"] == ["https://www.payback.de/*"]
    assert manifest["content_scripts"][0]["js"] == ["content-utils.js", "content.js"]
    assert "background" not in manifest
    assert "content_security_policy" not in manifest


def test_extension_is_standalone_and_content_extractor_is_read_only():
    expected = {
        "manifest.json",
        "popup.html",
        "popup.css",
        "popup.js",
        "popup-state.js",
        "content-utils.js",
        "content.js",
    }
    assert {path.name for path in EXTENSION_DIR.iterdir() if path.is_file()} == expected

    all_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in EXTENSION_DIR.iterdir()
        if path.suffix in {".js", ".html", ".css", ".json"}
    )
    content_source = "\n".join(
        (EXTENSION_DIR / name).read_text(encoding="utf-8")
        for name in ("content-utils.js", "content.js")
    )
    popup_html = (EXTENSION_DIR / "popup.html").read_text(encoding="utf-8")

    assert not re.search(r"https?://[^*\s\"']+\.(?:js|css)(?:[?\"'])", all_source)
    assert "eval(" not in all_source
    assert "new Function" not in all_source
    assert "chrome.cookies" not in all_source
    assert "webRequest" not in all_source
    assert "fetch(" not in content_source
    assert not re.search(
        r"\.(?:click|remove|append|prepend|replaceWith)\s*\(", content_source
    )
    assert "innerHTML" not in content_source
    assert '<script src="popup.js"></script>' in popup_html
    assert not re.search(r"<script(?![^>]+src=)", popup_html)


def test_extension_supports_accumulation_preview_shadow_dom_and_secure_cleanup():
    content_source = "\n".join(
        (EXTENSION_DIR / name).read_text(encoding="utf-8")
        for name in ("content-utils.js", "content.js")
    )
    popup_source = "\n".join(
        (EXTENSION_DIR / name).read_text(encoding="utf-8")
        for name in ("popup-state.js", "popup.js")
    )

    assert "shadowRoot" in content_source
    assert "balance" in content_source
    assert "expirations" in content_source
    assert "activities" in content_source
    assert "coupons" in content_source
    assert "unknown_dom_version" in content_source
    assert "chrome.permissions.request" in popup_source
    assert "chrome.storage.session" in popup_source
    assert "mergeCapture" in popup_source
    assert "dedupe" in popup_source
    assert "chrome.storage.session.remove" in popup_source
    assert "chrome.permissions.remove" in popup_source
    assert "STATE_TTL_MS" in popup_source
    assert 'url.protocol !== "https:"' in popup_source
    assert "/api/modules/haushaltsbuch/loyalty/payback/bridge/import" in popup_source


def test_extension_parses_common_euro_purchase_formats():
    utilities = EXTENSION_DIR / "content-utils.js"
    script = f"""
      require({json.dumps(str(utilities))});
      const parse = globalThis.PaybackBridgeContent.parseMoney;
      console.log(JSON.stringify([
        parse("Einkauf 45,99 €"),
        parse("Einkauf € 45,99"),
        parse("Einkauf 1.234,56 €"),
        parse("Einkauf 45,99 EUR")
      ]));
    """
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True
    )

    assert json.loads(result.stdout) == [
        {"purchase_amount_minor": 4599, "purchase_currency": "EUR"},
        {"purchase_amount_minor": 4599, "purchase_currency": "EUR"},
        {"purchase_amount_minor": 123456, "purchase_currency": "EUR"},
        {"purchase_amount_minor": 4599, "purchase_currency": "EUR"},
    ]


def test_coupon_candidate_filter_prefers_individual_cards_over_list_container():
    utilities = EXTENSION_DIR / "content-utils.js"
    script = f"""
      require({json.dumps(str(utilities))});
      const first = {{ name: "first", contains: () => false }};
      const second = {{ name: "second", contains: () => false }};
      const wrapper = {{
        name: "wrapper",
        contains: candidate => candidate === first || candidate === second
      }};
      const result = globalThis.PaybackBridgeContent.leafCandidates(
        [wrapper, first, second]
      );
      console.log(JSON.stringify(result.map(item => item.name)));
    """
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True
    )

    assert json.loads(result.stdout) == ["first", "second"]


def test_content_scripts_share_selector_version_and_capture_empty_page():
    utilities = EXTENSION_DIR / "content-utils.js"
    content = EXTENSION_DIR / "content.js"
    script = f"""
      globalThis.Element = class Element {{}};
      globalThis.ShadowRoot = class ShadowRoot {{}};
      globalThis.getComputedStyle = () => ({{
        display: "block", visibility: "visible", opacity: "1"
      }});
      const body = new Element();
      body.innerText = ""; body.textContent = ""; body.parentElement = null;
      body.getRootNode = () => ({{}});
      body.getBoundingClientRect = () => ({{ width: 20, height: 20 }});
      globalThis.document = {{
        body, title: "PAYBACK", querySelectorAll: () => []
      }};
      globalThis.location = {{ origin: "https://www.payback.de", pathname: "/" }};
      let listener;
      globalThis.chrome = {{ runtime: {{ onMessage: {{
        addListener: callback => {{ listener = callback; }}
      }} }} }};
      require({json.dumps(str(utilities))});
      require({json.dumps(str(content))});
      let response;
      listener({{ type: "PAYBACK_CAPTURE_VISIBLE" }}, null, value => {{ response = value; }});
      console.log(JSON.stringify(response));
    """
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True
    )
    response = json.loads(result.stdout)

    assert response["ok"] is True
    assert response["capture"]["selector_version"] == "payback-visible-v1"
    assert response["capture"]["warnings"] == ["unknown_dom_version"]


def test_extension_visibility_check_honors_transparent_ancestors():
    utilities = EXTENSION_DIR / "content-utils.js"
    script = f"""
      globalThis.Element = class Element {{}};
      globalThis.ShadowRoot = class ShadowRoot {{}};
      globalThis.getComputedStyle = element => ({{
        display: "block", visibility: "visible", opacity: element.opacity
      }});
      require({json.dumps(str(utilities))});
      const parent = new Element();
      parent.opacity = "0"; parent.parentElement = null;
      parent.getRootNode = () => ({{}});
      const child = new Element();
      child.opacity = "1"; child.parentElement = parent;
      child.getRootNode = () => ({{}});
      child.getBoundingClientRect = () => ({{ width: 20, height: 20 }});
      console.log(globalThis.PaybackBridgeContent.visible(child));
    """
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True
    )

    assert result.stdout.strip() == "false"
