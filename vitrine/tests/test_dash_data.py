"""S2 Zusammenbau der Statuszentrale: festes Schema, Schwärzung, Zwischenspeicher (SPEC-STATUSZENTRALE.md, S2)."""
from __future__ import annotations

from backend import dash_data as dd

SECRET = "geheim-token-123456"
KEYS = {"messages", "home", "hydra", "tasks", "machine", "mining", "github", "holiday", "updated"}


class Src:
    """Gefälschte Quellen; zählt Aufrufe."""
    def __init__(self, **over):
        self.calls = {}
        self.over = over

    def get(self, name, default):
        self.calls[name] = self.calls.get(name, 0) + 1
        v = self.over.get(name, default)
        if isinstance(v, Exception):
            raise v
        return v

    def sources(self):
        return {
            "messages": lambda: self.get("messages", {"new": [{"id": "a" * 12, "title": "T", "text": f"x {SECRET}",
                                                              "kind": "info", "count": 1, "time": "12:00"}],
                                                      "new_count": 1, "history": []}),
            "hydra": lambda: self.get("hydra", {"service": "active", "agents": 1, "errors_last_hour": 1,
                                                "errors": [{"source": "llm", "count": 1, "last": f"fail {SECRET}"}]}),
            "tasks": lambda: self.get("tasks", {"open": 1, "in_progress": 0,
                                                "top": [{"title": f"t {SECRET}", "priority": "high", "status": "open"}]}),
            "machine": lambda: self.get("machine", {"load": 0.5, "ram": 30, "gpu": 50, "disk_free_pct": 60, "uptime_h": 3}),
            "mining": lambda: self.get("mining", None),
            "holiday": lambda: self.get("holiday", "Tag der Deutschen Einheit"),
            "github": lambda: self.get("github", {"prs": [{"repo": "r", "number": 1, "title": f"pr {SECRET}",
                                                          "draft": False, "ci": "green"}], "error": None}),
        }


def _build(src, now=1000.0):
    return dd.Builder(src.sources(), secrets=lambda: {SECRET}, redact=lambda s: s.replace("ghp_X", "[REDACTED]"),
                      clock=lambda: now)


def test_schema_vollstaendig_auch_wenn_alles_fehlt():
    src = Src(**{k: OSError("weg") for k in ("messages", "home", "hydra", "tasks", "machine", "mining", "github", "holiday")})
    r = _build(src).get()
    assert set(r) == KEYS and all(r[k] is None for k in KEYS - {"updated"})


def test_secret_ueberall_geschwaerzt():
    r = _build(Src()).get()
    assert SECRET not in repr(r)
    assert r["tasks"]["top"][0]["title"].startswith("t ") and r["github"]["prs"][0]["ci"] == "green"


def test_mustererkennung_greift_auch():
    r = _build(Src(messages={"new": [{"id": "b" * 12, "title": "", "text": "key ghp_X", "kind": "info", "count": 1,
                                      "time": "1"}], "new_count": 1, "history": []})).get()
    assert "ghp_X" not in r["messages"]["new"][0]["text"]


def test_lokale_bereiche_5s_github_60s_zwischengespeichert():
    src = Src()
    t = [1000.0]
    b = dd.Builder(src.sources(), secrets=lambda: set(), redact=lambda s: s, clock=lambda: t[0])
    b.get()
    t[0] += 4
    b.get()
    assert src.calls["tasks"] == 1 and src.calls["github"] == 1
    t[0] += 2
    b.get()
    assert src.calls["tasks"] == 2 and src.calls["github"] == 1
    t[0] += 60
    b.get()
    assert src.calls["github"] == 2


def test_fehler_einer_quelle_laesst_rest_stehen():
    r = _build(Src(tasks=ValueError("kaputt"))).get()
    assert r["tasks"] is None and r["machine"]["ram"] == 30


def test_github_quelle_bekommt_token_nicht_ins_ergebnis(monkeypatch):
    from backend import dash_github
    token = "ghp_" + "B" * 36
    monkeypatch.setattr(dd, "_project_token", lambda ref: token)
    seen = {}

    def fake_open_prs(repos, tok):
        seen["tok"], seen["repos"] = tok, repos
        return {"prs": [{"repo": "x", "number": 1, "title": f"leak {token}", "draft": False, "ci": "none"}], "error": None}
    monkeypatch.setattr(dash_github, "open_prs", fake_open_prs)
    fn = dd.github_source({"github_project": "Hydrahive DEV", "github_repos": ["hydrahive/hydrahive2"]})
    r = dd.Builder({"github": fn}, secrets=lambda: set(), redact=lambda s: s, clock=lambda: 0.0).get()
    assert seen == {"tok": token, "repos": ["hydrahive/hydrahive2"]}
    assert token not in repr(r)


def test_invalidate_holt_bereich_sofort_neu():
    src = Src()
    t = [1000.0]
    b = dd.Builder(src.sources(), secrets=lambda: set(), redact=lambda s: s, clock=lambda: t[0])
    b.get()
    b.invalidate("messages")
    b.get()
    assert src.calls["messages"] == 2 and src.calls["tasks"] == 1


def test_layout_und_home_bereich_im_schema(monkeypatch):
    """S4: /data liefert immer die normalisierte Anordnung und den Bereich home (TTL 60 s)."""
    from renderer import dash_layout
    assert "home" in dd.AREAS and dd.TTL["home"] == 60.0
    cfg = dash_layout.normalize(dict(tasks_user="till", github_project="P", github_repos=[], order=["home", "messages"],
                                     hidden=["mining"], messages_max=2))
    seen = {}
    monkeypatch.setattr(dd, "default_sources", lambda data_dir, c: (seen.setdefault("cfg", c), {})[1])
    monkeypatch.setattr(dd, "_hh_secrets", lambda user: (lambda: set()))
    monkeypatch.setattr(dd, "_hh_redact", lambda s: s)
    dd._builders.clear()
    r = dd.build("/tmp/x", cfg)
    dd._builders.clear()
    assert r["layout"] == {"order": cfg["order"], "hidden": ["mining"], "messages_max": 2, "mining_in_machine": True}
    assert seen["cfg"]["messages_max"] == 2


def test_neue_anordnung_wirkt_ohne_neuen_zwischenspeicher(monkeypatch):
    """Nur Reihenfolge geändert → gleicher Builder (Daten-Cache bleibt), Layout trotzdem neu."""
    from renderer import dash_layout
    base = dict(tasks_user="till", github_project="P", github_repos=[])
    calls = []
    monkeypatch.setattr(dd, "default_sources", lambda data_dir, c: (calls.append(1), {})[1])
    monkeypatch.setattr(dd, "_hh_secrets", lambda user: (lambda: set()))
    monkeypatch.setattr(dd, "_hh_redact", lambda s: s)
    dd._builders.clear()
    a = dd.build("/tmp/x", dash_layout.normalize(dict(base, order=["home"])))
    b = dd.build("/tmp/x", dash_layout.normalize(dict(base, order=["tasks"])))
    dd._builders.clear()
    assert len(calls) == 1 and a["layout"]["order"][0] == "home" and b["layout"]["order"][0] == "tasks"


def test_meldungen_hoechstens_n_aus_einstellung(tmp_path):
    from backend import dash_sources as ds
    from renderer import inbox
    for i in range(6):
        inbox.post(tmp_path, f"m{i}", now=1000.0 + i)
    r = ds.messages(tmp_path, now=1010.0, new_max=2)
    assert len(r["new"]) == 2 and r["new_count"] == 6
