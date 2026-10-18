"""S1 Backend: Rückkehrzeit (Config/Schema/Dienst gleich), Kiosk-Schlüssel, Platzhalter-Seite, „Zurück“, Status-Felder."""
from __future__ import annotations

import json

import pytest

from renderer import config as cfg
from renderer import mode


def test_rueckkehrzeit_in_config_mit_grenzen(tmp_path):
    assert cfg.load(tmp_path)["dashboard_return_seconds"] == 120
    for v, want in ((45, 45), (29, 120), (1801, 120), ("x", 120), (True, 120)):
        (tmp_path / "config.json").write_text(json.dumps({"dashboard_return_seconds": v}))
        assert cfg.load(tmp_path)["dashboard_return_seconds"] == want
    assert cfg.RETURN_RANGE == mode.RETURN_RANGE and cfg.DEFAULTS["dashboard_return_seconds"] == mode.RETURN_DEFAULT


def test_schema_grenzen_gleich_wie_dienst():
    pytest.importorskip("pydantic")
    from backend.schemas import Config
    f = Config.model_fields["dashboard_return_seconds"]
    ge = next(m.ge for m in f.metadata if getattr(m, "ge", None) is not None)
    le = next(m.le for m in f.metadata if getattr(m, "le", None) is not None)
    assert (ge, le) == mode.RETURN_RANGE and f.default == mode.RETURN_DEFAULT


def test_kiosk_schluessel_vergleich(tmp_path):
    from backend import kiosk
    assert not kiosk.key_ok(tmp_path, "abc")                       # keine Schlüsseldatei → nie
    (tmp_path / "kiosk.key").write_text("a" * 64 + "\n")
    assert kiosk.key_ok(tmp_path, "a" * 64)
    assert not kiosk.key_ok(tmp_path, "a" * 63 + "b")
    assert not kiosk.key_ok(tmp_path, "") and not kiosk.key_ok(tmp_path, None)
    (tmp_path / "kiosk.key").write_text("kurz")
    assert not kiosk.key_ok(tmp_path, "kurz"), "zu kurzer Schlüssel gilt nicht"


@pytest.mark.parametrize(("host", "ok"), [("127.0.0.1", True), ("::1", True), ("192.168.178.20", False), ("?", False)])
def test_nur_von_localhost(host, ok):
    from backend import kiosk
    assert kiosk.local_ok(host) is ok


def test_platzhalter_seite_ohne_daten_mit_zurueck_knopf():
    from backend import kiosk
    html = kiosk.page("SCHLUESSEL")
    assert "<button" in html and "Zurück" in html and "SCHLUESSEL" in html
    assert "fetch(\"back?k=" in html                  # relativ zu /api/module-device/vitrine/kiosk
    for verboten in ("/api/modules/", "token", "session", "authorization"):   # S1: keine Daten-Abfragen, keine Zugänge
        assert verboten not in html.lower()
    assert html.count("fetch(") == 1, "einzige Anfrage: Zurück-Knopf"


def test_status_enthaelt_modus_und_dashboard(tmp_path):
    from backend import state
    import time
    (tmp_path / "state.json").write_text(json.dumps({"updated": time.time(), "mode": "dashboard", "dashboard": "bereit"}))
    info = state.program_info(tmp_path)
    assert info["mode"] == "dashboard" and info["dashboard"] == "bereit"


def test_zurueck_schreibt_wunsch(tmp_path):
    from backend import kiosk
    kiosk.back(tmp_path)
    assert mode.take_back_request(tmp_path) is True
