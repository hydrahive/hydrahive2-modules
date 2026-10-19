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


def test_seite_ohne_daten_nur_data_und_zurueck():
    from backend import kiosk
    html = kiosk.page("SCHLUESSEL")
    assert "<button" in html and "Zurück zum Video" in html and "SCHLUESSEL" in html
    assert 'fetch("back?k=' in html and 'fetch("data?k=' in html     # relativ zu /api/module-device/vitrine/kiosk
    assert 'fetch("read?k=' in html                                  # S3: Gelesen
    assert html.count("fetch(") == 3, "nur Daten, Zurück, Gelesen"
    for verboten in ("/api/modules/", "authorization", "innerhtml", "outerhtml", "insertadjacenthtml", "document.write",
                     "eval(", "<script src", "<link", "http://", "https://"):
        assert verboten not in html.lower(), verboten
    assert html.count("<button") == 1, "fest im HTML nur „Zurück“; „Gelesen“ entsteht je Meldung per createElement"
    assert 'createElement("button")' in html and "Gelesen" in html and "Keine neuen Meldungen" in html
    assert "Verlauf" in html and "weitere" in html
    assert "HydraHive antwortet nicht" in html


def test_seite_schluessel_wird_escaped():
    from backend import kiosk
    html = kiosk.page('a"</script><script>alert(1)//')
    assert "</script><script>alert(1)" not in html


def test_seite_fuer_sofa_lesbar():
    import re
    from backend import kiosk
    html = kiosk.page("K")
    sizes = [int(x) for x in re.findall(r"font-size:(\d+)px", html)]
    assert sizes and min(sizes) >= 32


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


def test_config_dashboard_standard_und_pruefung(tmp_path):
    from renderer import config
    assert config.load(tmp_path)["dashboard"]["github_project"] == "Hydrahive DEV"
    for bad in ({"tasks_user": "../x", "github_project": "P", "github_repos": []},
                {"tasks_user": "till", "github_project": "P", "github_repos": ["a/.."]},
                {"tasks_user": "till", "github_project": "P", "github_repos": ["https://evil/x"]},
                {"tasks_user": "till", "github_project": " ", "github_repos": []},
                {"tasks_user": "till", "github_project": "P", "github_repos": ["a/b"] * 6},
                {"tasks_user": "till", "github_project": "P", "github_repos": [], "token": "x"}):
        (tmp_path / "config.json").write_text(json.dumps({"dashboard": bad}))
        assert config.load(tmp_path)["dashboard"]["tasks_user"] == "till"
        assert config.load(tmp_path)["dashboard"]["github_project"] == "Hydrahive DEV", bad
    good = {"tasks_user": "anna", "github_project": "X", "github_repos": ["o/r"]}
    (tmp_path / "config.json").write_text(json.dumps({"dashboard": good}))
    assert config.load(tmp_path)["dashboard"] == good


def test_schema_dashboard_lehnt_ab():
    import pytest as _p
    _p.importorskip("pydantic")
    from pydantic import ValidationError
    from backend.schemas import Config
    assert Config().dump()["dashboard"]["github_repos"] == ["hydrahive/hydrahive2.0", "hydrahive/hydrahive2-modules"]
    for bad in ({"github_repos": ["a/b/c"]}, {"tasks_user": "a b"}, {"github_project": ""}, {"token": "x"}):
        with _p.raises(ValidationError):
            Config(dashboard=bad)


def test_installer_startet_kiosk_firefox_neu():
    """Abnahme 19.10.: nach dem Update lief die alte Seite weiter – Installer muss Firefox neu starten."""
    from pathlib import Path
    s = (Path(__file__).resolve().parents[1] / "extension" / "kiosk-install.sh").read_text()
    assert 'pkill -u "${KIOSK}" -f "firefox --kiosk"' in s
    assert s.index("pkill -u") > s.index('cat > "${HOME_DIR}/vitrine/start.html"'), "erst neue Startseite, dann Neustart"
