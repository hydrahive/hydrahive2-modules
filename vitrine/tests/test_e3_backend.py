"""E3 im HydraHive-Prozess: Werkzeug display_message, Butler-Aktion, Fehler-/Status-Job."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("hydrahive")


@pytest.fixture
def data(tmp_path, monkeypatch):
    from backend import notify
    monkeypatch.setattr(notify, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(notify, "_secrets", lambda user, agent: {"geheim-token-123456"})
    notify._last_shown.clear()
    yield tmp_path
    notify._last_shown.clear()


def _ctx():
    return SimpleNamespace(user_id="till", agent_id="a1", session_id="s1", workspace=Path("/tmp"), project_id=None)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_werkzeug_legt_nachricht_ab(data):
    from backend import tools
    r = _run(tools.DISPLAY_TOOL.execute({"text": "Backup fertig ✓", "kind": "success", "seconds": 20}, _ctx()))
    assert r.success, r.error
    from renderer import inbox
    [m] = inbox.active(data)
    assert m["text"] == "Backup fertig ✓" and m["kind"] == "success" and m["source"].startswith("agent:")


def test_werkzeug_schwaerzt_geheimnisse(data):
    from backend import tools
    _run(tools.DISPLAY_TOOL.execute({"text": "Token ist geheim-token-123456 – bitte nicht zeigen"}, _ctx()))
    from renderer import inbox
    [m] = inbox.active(data)
    assert "geheim-token-123456" not in m["text"]


@pytest.mark.parametrize("args", [{"text": ""}, {"text": "x", "kind": "laser"}, {"text": "x", "seconds": 1}, {}])
def test_werkzeug_fehler_ohne_ablage(data, args):
    from backend import tools
    r = _run(tools.DISPLAY_TOOL.execute(args, _ctx()))
    assert not r.success
    assert not (data / "inbox").exists() or list((data / "inbox").iterdir()) == []


def test_werkzeug_standardmaessig_aus():
    import json as _j
    m = _j.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
    assert m["default_agent_tools"] is False


def test_butler_aktion_rendert_vorlage(data):
    from backend import butler
    from hydrahive.butler.models import TriggerEvent
    ev = TriggerEvent(event_type="message_in", channel="discord", contact_label="Bibi", message_text="Bin gleich da")
    res = _run(butler.ACTION.execute({"text": "{{event.contact_label}}: {{event.message_text}}", "kind": "info", "seconds": 30}, ev))
    assert res.ok
    from renderer import inbox
    [m] = inbox.active(data)
    assert m["text"] == "Bibi: Bin gleich da" and m["source"] == "butler"


def test_butler_aktion_leerer_text_scheitert(data):
    from backend import butler
    from hydrahive.butler.models import TriggerEvent
    res = _run(butler.ACTION.execute({"text": "   "}, TriggerEvent(event_type="manual")))
    assert not res.ok


def _errors(rows):
    return lambda since: [r for r in rows if r["created_at"] > since]


def test_fehler_werden_eingeblendet_und_gedrosselt(data, monkeypatch):
    from backend import notify
    rows = [{"created_at": "2026-10-15T20:00:01", "source": "runner.llm_call", "severity": "error", "error_message": "429 Too Many Requests"},
            {"created_at": "2026-10-15T20:00:02", "source": "runner.llm_call", "severity": "error", "error_message": "429 again"},
            {"created_at": "2026-10-15T20:00:03", "source": "mirror.write_event", "severity": "critical", "error_message": "DB weg"}]
    monkeypatch.setattr(notify, "_errors_since", _errors(rows))
    monkeypatch.setattr(notify, "_active_agents", lambda: 2)
    notify.tick(now=1000.0)
    from renderer import inbox
    texts = sorted(m["title"] for m in inbox.active(data, now=1000.0))
    assert texts == ["Fehler: mirror.write_event", "Fehler: runner.llm_call"], "pro Quelle nur eine Einblendung"
    st = json.loads((data / "hydra.json").read_text())
    assert st["agents"] == 2 and st["errors_last_hour"] == 3


def test_kein_doppel_nach_neustart(data, monkeypatch):
    from backend import notify
    rows = [{"created_at": "2026-10-15T20:00:01", "source": "x", "severity": "error", "error_message": "kaputt"}]
    monkeypatch.setattr(notify, "_errors_since", _errors(rows))
    monkeypatch.setattr(notify, "_active_agents", lambda: 0)
    notify.tick(now=1000.0)
    notify._last_shown.clear()                  # „Neustart“ – Merker liegt in der Datei
    notify.tick(now=1030.0)
    from renderer import inbox
    assert len(inbox.active(data, now=1030.0)) == 1


def test_gleiche_quelle_erst_nach_zehn_minuten_wieder(data, monkeypatch):
    from backend import notify
    from renderer import inbox
    rows, posted = [], []
    orig = inbox.post
    monkeypatch.setattr(inbox, "post", lambda d, text, **kw: posted.append(text) or orig(d, text, **kw))
    monkeypatch.setattr(notify, "_errors_since", _errors(rows))
    monkeypatch.setattr(notify, "_active_agents", lambda: 0)
    rows.append({"created_at": "2026-10-15T20:00:01", "source": "x", "severity": "error", "error_message": "a"})
    notify.tick(now=1000.0)
    rows.append({"created_at": "2026-10-15T20:01:00", "source": "x", "severity": "error", "error_message": "b"})
    notify.tick(now=1060.0)
    rows.append({"created_at": "2026-10-15T20:12:00", "source": "x", "severity": "error", "error_message": "c"})
    notify.tick(now=1000.0 + 11 * 60)
    assert posted == ["a", "c"]


def test_warnungen_werden_nicht_eingeblendet(data, monkeypatch):
    from backend import notify
    monkeypatch.setattr(notify, "_errors_since", _errors([{"created_at": "2026-10-15T20:00:01", "source": "x", "severity": "warning", "error_message": "w"}]))
    monkeypatch.setattr(notify, "_active_agents", lambda: 0)
    notify.tick(now=1000.0)
    from renderer import inbox
    assert inbox.active(data, now=1000.0) == []


def test_hoechstens_sechs_fehlerkarten_pro_stunde(data, monkeypatch):
    from backend import notify
    from renderer import inbox
    rows, posted = [], []
    orig = inbox.post
    monkeypatch.setattr(inbox, "post", lambda d, text, **kw: posted.append(text) or orig(d, text, **kw))
    monkeypatch.setattr(notify, "_errors_since", _errors(rows))
    monkeypatch.setattr(notify, "_active_agents", lambda: 0)
    rows += [{"created_at": f"2026-10-15T20:00:{i:02d}", "source": f"q{i}", "severity": "error", "error_message": f"m{i}"} for i in range(9)]
    notify.tick(now=1000.0)
    assert len(posted) == 6
    rows.append({"created_at": "2026-10-15T20:05:00", "source": "neu", "severity": "error", "error_message": "neu"})
    notify.tick(now=1300.0)
    assert len(posted) == 6, "Stundenbudget aufgebraucht"


def test_butler_aktion_name():
    from backend import butler
    assert butler.ACTION.subtype == "vitrine_message"


def test_erster_start_holt_alte_fehler_nicht_nach(data, monkeypatch):
    from backend import notify
    from renderer import inbox
    import datetime as _dt
    alt = _dt.datetime.fromtimestamp(1000.0 - 120, _dt.timezone.utc).isoformat(timespec="milliseconds")
    monkeypatch.setattr(notify, "_errors_since", _errors([{"created_at": alt, "source": "x", "severity": "error", "error_message": "alt"}]))
    monkeypatch.setattr(notify, "_active_agents", lambda: 0)
    notify.tick(now=1000.0)
    assert inbox.active(data, now=1000.0) == []
    assert json.loads((data / "hydra.json").read_text())["errors_last_hour"] == 1, "zählt trotzdem für die Leiste"
