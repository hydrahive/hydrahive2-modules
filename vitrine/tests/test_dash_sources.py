"""S2 Datenquellen der Statuszentrale: je Bereich fehlertolerant, mit Test-Datenbank (Tabellen fehlen/leer/gefüllt)."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager

from backend import dash_sources as ds


def _db(tmp_path, *ddl):
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    for stmt in ddl:
        con.executescript(stmt)
    con.commit()
    con.close()

    @contextmanager
    def connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()
    return connect


TASKS = """CREATE TABLE module_tasks (id TEXT, username TEXT, project_id TEXT, session_id TEXT, title TEXT,
           description TEXT, status TEXT, priority TEXT, created_at TEXT, updated_at TEXT);"""
ERRORS = """CREATE TABLE errors_log (id INTEGER, created_at TEXT, session_id TEXT, agent_id TEXT, user_id TEXT,
            source TEXT, severity TEXT, error_type TEXT, error_message TEXT, traceback TEXT, context TEXT);"""
MINING = """CREATE TABLE module_mining_rigs (id TEXT, name TEXT, status TEXT, enabled INTEGER, last_report TEXT,
            last_seen TEXT, token_hash TEXT);
            CREATE TABLE module_mining_samples (rig_id TEXT, ts TEXT, data TEXT);
            CREATE TABLE module_mining_config (key TEXT, value TEXT);"""


def _iso(t: float) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="milliseconds")


def test_tasks_fehlende_tabelle_none(tmp_path):
    assert ds.tasks("till", connect=_db(tmp_path)) is None


def test_tasks_zahl_und_top5_nach_prioritaet_dann_alter(tmp_path):
    con = _db(tmp_path, TASKS)
    rows = [("a", "low", "2026-01-01"), ("b", "high", "2026-03-01"), ("c", "high", "2026-02-01"), ("d", "medium", "2026-01-05"),
            ("e", "medium", "2026-01-02"), ("f", "low", "2025-01-01"), ("g", "high", "2026-04-01")]
    with con() as c:
        for i, (t, p, at) in enumerate(rows):
            c.execute("INSERT INTO module_tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (str(i), "till", None, None, t, "", "open" if i % 2 else "in_progress", p, at, at))
        c.execute("INSERT INTO module_tasks VALUES ('x','till',NULL,NULL,'erledigt','', 'done','high','2020','2020')")
        c.execute("INSERT INTO module_tasks VALUES ('y','anna',NULL,NULL,'fremd','', 'open','high','2020','2020')")
        c.commit()
    r = ds.tasks("till", connect=con)
    assert r["open"] == 3 and r["in_progress"] == 4
    assert [t["title"] for t in r["top"]] == ["c", "b", "g", "e", "d"]
    assert r["top"][0]["priority"] == "high" and r["top"][0]["status"] in ("open", "in_progress")


def test_tasks_titel_gekuerzt(tmp_path):
    con = _db(tmp_path, TASKS)
    with con() as c:
        c.execute("INSERT INTO module_tasks VALUES ('1','till',NULL,NULL,?,'','open','high','2026','2026')", ("x" * 300,))
        c.commit()
    assert len(ds.tasks("till", connect=con)["top"][0]["title"]) <= ds.TITLE_MAX


def test_hydra_fehler_je_quelle_nur_letzte_stunde(tmp_path):
    con = _db(tmp_path, ERRORS)
    now = time.time()
    with con() as c:
        for i, (ago, src, sev, msg) in enumerate([(100, "llm", "error", "alt1"), (50, "llm", "error", "neu"),
                                                  (30, "tools", "critical", "kaputt"), (20, "x", "warning", "egal"),
                                                  (4000, "llm", "error", "zu alt")]):
            c.execute("INSERT INTO errors_log (id, created_at, source, severity, error_message) VALUES (?,?,?,?,?)",
                      (i, _iso(now - ago), src, sev, msg))
        c.commit()
    r = ds.hydra(connect=con, active=lambda: 3, service=lambda: "active", now=now)
    assert r["agents"] == 3 and r["service"] == "active" and r["errors_last_hour"] == 3
    by = {e["source"]: e for e in r["errors"]}
    assert by["llm"]["count"] == 2 and by["llm"]["last"] == "neu" and by["tools"]["count"] == 1
    assert "x" not in by, "Warnungen zählen nicht"


def test_hydra_ohne_tabelle_trotzdem_dienst_und_agenten(tmp_path):
    r = ds.hydra(connect=_db(tmp_path), active=lambda: 0, service=lambda: "active", now=time.time())
    assert r["agents"] == 0 and r["errors"] == [] and r["errors_last_hour"] == 0


def test_mining_fehlende_tabelle_none(tmp_path):
    assert ds.mining(connect=_db(tmp_path), now=time.time()) is None


def test_mining_eur_tag_und_rechner(tmp_path):
    con = _db(tmp_path, MINING)
    now = time.time()
    with con() as c:
        c.execute("INSERT INTO module_mining_rigs VALUES ('r1','rig-01','active',1,NULL,NULL,'h')")
        c.execute("INSERT INTO module_mining_rigs VALUES ('r2','rig-02','active',0,NULL,NULL,'h')")
        c.execute("INSERT INTO module_mining_rigs VALUES ('r3','rig-alt','revoked',1,NULL,NULL,'h')")
        c.execute("INSERT INTO module_mining_samples VALUES ('r1',?,?)", (_iso(now - 600), json.dumps({"usd_day": 1.0})))
        c.execute("INSERT INTO module_mining_samples VALUES ('r1',?,?)", (_iso(now - 60), json.dumps({"usd_day": 2.2})))
        c.execute("INSERT INTO module_mining_config VALUES ('_usd_per_eur', '1.1')")
        c.commit()
    r = ds.mining(connect=con, now=now)
    assert [x["name"] for x in r["rigs"]] == ["rig-01", "rig-02"], "gesperrte Rechner fehlen"
    assert abs(r["eur_day"] - 2.0) < 1e-9
    assert {x["name"]: x["mining"] for x in r["rigs"]} == {"rig-01": True, "rig-02": False}


def test_mining_probe_genau_an_der_grenze_zaehlt(tmp_path):
    """Mining speichert ts ohne Millisekunden (history.record) – Grenze muss im selben Format verglichen werden."""
    import datetime as dt
    con = _db(tmp_path, MINING)
    now = 1_800_000_000.0
    with con() as c:
        c.execute("INSERT INTO module_mining_rigs VALUES ('r1','rig-01','active',1,NULL,NULL,'h')")
        c.execute("INSERT INTO module_mining_samples VALUES ('r1',?,?)",
                  (dt.datetime.fromtimestamp(now - 900, dt.timezone.utc).isoformat(), json.dumps({"usd_day": 3.0})))
        c.execute("INSERT INTO module_mining_config VALUES ('_usd_per_eur', '1.5')")
        c.commit()
    assert ds.mining(connect=con, now=now)["eur_day"] == 2.0


def test_rechner_werte(monkeypatch):
    r = ds.machine(status=lambda: {"hydra": "active", "load": 1.5, "ram": 40, "gpu": 55}, disk=lambda: (100, 25),
                   uptime=lambda: 90061.0)
    assert r == {"load": 1.5, "ram": 40, "gpu": 55, "disk_free_pct": 25, "uptime_h": 25}


def test_meldung_neueste_sichtbare(tmp_path):
    from renderer import inbox
    assert ds.message(tmp_path) is None
    inbox.post(tmp_path, "erste", title="A", kind="info")
    time.sleep(0.01)
    inbox.post(tmp_path, "zweite", title="B", kind="error")
    m = ds.message(tmp_path)
    assert m["title"] in ("A", "B") and m["kind"] in ("info", "error") and set(m) == {"title", "text", "kind"}


def test_quelle_mit_fehler_wird_none(tmp_path):
    def kaputt():
        raise sqlite3.OperationalError("database is locked")
    assert ds.safe(lambda: ds.tasks("till", connect=lambda: kaputt())) is None
