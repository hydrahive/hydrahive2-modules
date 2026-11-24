"""Multiseat M2b: POST /seats/apply und /seats/revert über den echten Kern-Weg (nur Admin).

`subprocess.run` ist ersetzt (nichts läuft als root), /etc/hydrahive2-vitrine liegt unter tmp. Geprüft wird der genaue
Root-Aufruf, die drei geschriebenen Dateien, 409/422 und der Status in GET /seats.
"""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import json
import threading
import time

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _h, admin, client, data, env  # noqa: F401 - pytest-Fixtures
from _seats_fixture import NV, build


class FakeRun:
    """Ersatz für subprocess.run: merkt sich den Aufruf; `gate` hält den Lauf an (für 409-Tests)."""

    def __init__(self, code: int = 0, out: str = "ok\n"):
        self.calls: list[list[str]] = []
        self.code, self.out = code, out
        self.gate = threading.Event()
        self.gate.set()

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        self.gate.wait(10)
        import subprocess
        return subprocess.CompletedProcess(cmd, self.code, stdout=self.out, stderr="")


@pytest.fixture
def sw(tmp_path, monkeypatch, data):
    from backend import seat_apply_routes, seat_routes
    for n in ("plan.json", "lightdm.conf", "xorg.conf", "last-run.json"):   # Datenordner gilt je Testdatei
        (data / "multiseat" / n).unlink(missing_ok=True)
    monkeypatch.setattr(seat_routes, "SYS_ROOT", build(tmp_path / "sys"))
    etc = tmp_path / "etc-vitrine"
    etc.mkdir()
    monkeypatch.setattr(seat_apply_routes, "ETC", etc)
    fake = FakeRun()
    monkeypatch.setattr(seat_apply_routes.subprocess, "run", fake)
    fake.etc = etc
    yield fake
    fake.gate.set()
    _wait_idle()


def _wait_idle():
    from backend import seat_apply_routes
    for _ in range(200):
        if seat_apply_routes._running["action"] is None:
            return
        time.sleep(0.02)
    raise AssertionError("Lauf endet nicht")


def _save(client, admin, **extra):
    v = client.get(f"{B}/seats", headers=admin).json()
    a = {d["id"]: "seat0" for k in ("gpus", "sound", "inputs") for d in v["devices"][k]}
    a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1", **extra})
    assert client.put(f"{B}/seats", json={"assignment": a}, headers=admin).status_code == 200


def test_apply_schreibt_dateien_und_ruft_root_weg(client, admin, data, sw):
    from backend import seat_apply_routes
    _save(client, admin)
    r = client.post(f"{B}/seats/apply", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["running"] == "apply"
    _wait_idle()
    d = data / "multiseat"
    for n in ("plan.json", "lightdm.conf", "xorg.conf"):
        assert (d / n).is_file() and (d / n).stat().st_mode & 0o777 == 0o644
    plan = json.loads((d / "plan.json").read_text())
    assert plan["seat0_busid"] == "PCI:13:0:0" and len(plan["attach"]) == 3
    assert "[Seat:seat0]" in (d / "lightdm.conf").read_text()
    script = seat_apply_routes.MODULE_ROOT / "extension" / "multiseat-apply.sh"
    assert sw.calls == [["sudo", "-n", "bash", "-c",
                         f"systemd-run --quiet --wait --pipe --collect /bin/bash {script} {d / 'plan.json'} "
                         f"{d / 'lightdm.conf'} {d / 'xorg.conf'}"]]
    last = json.loads((d / "last-run.json").read_text())
    assert last["action"] == "apply" and last["exit"] == 0 and last["ok"] is True and last["lines"] == ["ok"]
    v = client.get(f"{B}/seats", headers=admin).json()
    assert v["running"] is None and v["last_run"]["exit"] == 0 and v["applied"] is False   # Marker setzt nur root


def test_get_applied_liest_marker(client, admin, data, sw):
    assert client.get(f"{B}/seats", headers=admin).json()["applied"] is False
    (sw.etc / "multiseat.aktiv").write_text("seit=x\n")
    assert client.get(f"{B}/seats", headers=admin).json()["applied"] is True
    _save(client, admin)
    r = client.post(f"{B}/seats/apply", headers=admin)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "vitrine_seat_already_on" and sw.calls == []


def test_apply_ohne_gespeicherte_zuordnung_422(client, admin, data, sw):
    (data / "seats.json").unlink(missing_ok=True)
    r = client.post(f"{B}/seats/apply", headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "vitrine_seat_not_saved" and sw.calls == []
    assert client.get(f"{B}/seats", headers=admin).json()["saved_error"] == "vitrine_seat_not_saved"


def test_apply_zuordnung_passt_nicht_mehr_422(client, admin, data, sw):
    """Gespeichert, aber Gerät inzwischen weg (seats.json von Hand / altes System) → 422 mit Code, kein Lauf."""
    _save(client, admin)
    s = json.loads((data / "seats.json").read_text())
    s["assignment"]["input:usb:9-9"] = "seat1"
    (data / "seats.json").write_text(json.dumps(s))
    r = client.post(f"{B}/seats/apply", headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "vitrine_seat_unknown_device" and sw.calls == []
    assert not (data / "multiseat" / "plan.json").exists()


def test_apply_bluetooth_an_seat1_422(client, admin, data, sw, tmp_path, monkeypatch):
    from _seats_fixture import BT_KB, K400, RAPOO

    from backend import seat_routes
    monkeypatch.setattr(seat_routes, "SYS_ROOT", build(tmp_path / "bt", inputs=BT_KB + K400 + RAPOO))
    _save(client, admin, **{"input:bt:aa:bb:cc:dd:ee:ff": "seat1"})
    r = client.post(f"{B}/seats/apply", headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "vitrine_seat_plan_bt_seat1"
    assert client.get(f"{B}/seats", headers=admin).json()["saved_error"] == "vitrine_seat_plan_bt_seat1"


def test_zweiter_lauf_gleichzeitig_409(client, admin, data, sw):
    _save(client, admin)
    sw.gate.clear()
    assert client.post(f"{B}/seats/apply", headers=admin).status_code == 200
    assert client.get(f"{B}/seats", headers=admin).json()["running"] == "apply"
    (sw.etc / "multiseat-revert.sh").write_text("#!/bin/bash\n")
    for path in ("apply", "revert"):
        r = client.post(f"{B}/seats/{path}", headers=admin)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "vitrine_seat_busy"
    sw.gate.set()
    _wait_idle()
    assert len(sw.calls) == 1


def test_revert_ohne_skript_409(client, admin, data, sw):
    r = client.post(f"{B}/seats/revert", headers=admin)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "vitrine_seat_not_on" and sw.calls == []


def test_revert_ruft_root_weg_und_meldet_fehler(client, admin, data, sw):
    (sw.etc / "multiseat-revert.sh").write_text("#!/bin/bash\n")
    sw.code, sw.out = 3, "Vitrine-Multiseat: Vitrine-Sitzung nach dem Rückbau nicht gefunden. Rechner neu starten\n"
    assert client.post(f"{B}/seats/revert", headers=admin).status_code == 200
    _wait_idle()
    assert sw.calls == [["sudo", "-n", "bash", "-c",
                         f"systemd-run --quiet --wait --pipe --collect /bin/bash {sw.etc / 'multiseat-revert.sh'}"]]
    last = client.get(f"{B}/seats", headers=admin).json()["last_run"]
    assert last["action"] == "revert" and last["exit"] == 3 and last["ok"] is False and "neu starten" in last["lines"][0]


def test_nur_admin_darf_schalten(client, data, sw):
    for path in ("apply", "revert"):
        assert client.post(f"{B}/seats/{path}", headers=_h(client, "nutzer")).status_code == 403
        assert client.post(f"{B}/seats/{path}").status_code == 401
    assert sw.calls == []


def test_root_aufruf_quotet_pfade():
    """Pfade stammen aus Modul/Datenordner; trotzdem sicher gequotet (Leerzeichen, Anführungszeichen)."""
    from pathlib import Path

    from backend.seat_apply_routes import root_cmd
    cmd = root_cmd(Path("/opt/a b/apply.sh"), Path("/d/it's.json"))
    assert cmd[:4] == ["sudo", "-n", "bash", "-c"]
    assert cmd[4] == "systemd-run --quiet --wait --pipe --collect /bin/bash '/opt/a b/apply.sh' '/d/it'\"'\"'s.json'"
