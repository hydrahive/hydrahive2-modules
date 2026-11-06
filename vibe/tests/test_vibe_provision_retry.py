"""Einrichtung: Netz-Schritte werden bei Aussetzern wiederholt, der Fehlergrund wird festgehalten (PLAN-V1.md Baustein 7).

Befund hydratest 5.11.2026: Beim Anlegen scheiterte `npm ci` einmal mit `vibe_setup_failed`, derselbe Befehl lief direkt
danach in 2 s durch und „Nochmal versuchen“ brachte das Projekt in 3 s auf `ready`. Ein Aussetzer des Netzes, aber das
Modul behielt von dem Fehler nichts, und es wiederholte nichts.

Vertrag:
- Nur Schritte mit Netz (`packages`, `node`, `deps`, `devserver`) werden bis zu 3-mal versucht; die anderen genau einmal
  (sie sind lokal und ein Fehler dort ist kein Aussetzer).
- Pause zwischen den Versuchen kurz und wachsend, nie lang.
- Nach dem letzten Versuch: Fehler mit dem Schritt UND den letzten Zeilen der Ausgabe (gekürzt, ohne Steuerzeichen).
- Ein Zeitlimit des incus-Aufrufs zählt wie ein Fehlschlag; Abbruch von außen läuft unverändert durch.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import provision
from hydrahive.containers.incus_client import IncusError

NET = ("packages", "node", "deps", "devserver")
LOCAL = ("user", "template", "git")


def run(coro):
    return asyncio.run(coro)


class Script:
    """Ersatz für `incus.run`: je Schritt (erkannt am Skripttext) eine Folge von Ergebnissen."""

    def __init__(self) -> None:
        self.plan: dict[str, list] = {}            # Schrittname → Liste von (rc, out, err) oder Exception
        self.calls: dict[str, int] = {}
        self.order: list[str] = []

    def key_of(self, args) -> str:
        body = " ".join(args)
        for s in provision.STEPS:
            if s.script[:60] in body:
                return s.key
        return "?"

    async def run(self, *args, timeout=0, input_bytes=None):
        k = self.key_of(args)
        self.calls[k] = self.calls.get(k, 0) + 1
        self.order.append(k)
        seq = self.plan.get(k)
        item = seq.pop(0) if seq else (0, "", "")
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def sc(monkeypatch):
    s = Script()
    monkeypatch.setattr(provision.incus, "run", s.run)
    waits: list[float] = []

    async def spy(x):
        waits.append(x)
    monkeypatch.setattr(provision.asyncio, "sleep", spy)
    s.waits = waits
    return s


FAIL = (1, "", "npm error network request failed")


def setup(project="p1"):
    return run(provision.setup(project, lambda _k: None))


def test_versuche_sind_drei():
    assert provision.NET_ATTEMPTS == 3


def test_netzschritte_sind_festgelegt():
    assert tuple(s.key for s in provision.STEPS if s.net) == NET


@pytest.mark.parametrize("key", NET)
def test_netzschritt_zwei_aussetzer_dann_erfolg(sc, key):
    sc.plan[key] = [FAIL, FAIL]
    setup()
    assert sc.calls[key] == 3


@pytest.mark.parametrize("key", NET)
def test_netzschritt_dreimal_fehler_scheitert(sc, key):
    sc.plan[key] = [FAIL, FAIL, FAIL]
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert e.value.step == key and sc.calls[key] == 3


@pytest.mark.parametrize("key", LOCAL)
def test_lokaler_schritt_wird_nicht_wiederholt(sc, key):
    sc.plan[key] = [(1, "", "kaputt")]
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert e.value.step == key and sc.calls[key] == 1


def test_nach_erfolg_geht_es_mit_dem_naechsten_schritt_weiter(sc):
    sc.plan["deps"] = [FAIL]
    setup()
    first_deps = sc.order.index("deps")
    assert sc.order[first_deps:first_deps + 3] == ["deps", "deps", "devserver"]


def test_pause_zwischen_versuchen_kurz_und_wachsend(sc):
    sc.plan["deps"] = [FAIL, FAIL]
    setup()
    assert len(sc.waits) == 2 and sc.waits[0] < sc.waits[1] <= 10


def test_keine_pause_nach_dem_letzten_versuch(sc):
    sc.plan["deps"] = [FAIL, FAIL, FAIL]
    with pytest.raises(provision.SetupError):
        setup()
    assert len(sc.waits) == 2


def test_keine_pause_ohne_fehler(sc):
    setup()
    assert sc.waits == []


def test_zeitlimit_des_aufrufs_zaehlt_wie_fehlschlag(sc):
    sc.plan["deps"] = [IncusError("incus_timeout"), (0, "", "")]
    setup()
    assert sc.calls["deps"] == 2


def test_zeitlimit_dreimal_scheitert_mit_schritt(sc):
    sc.plan["deps"] = [IncusError("incus_timeout")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert e.value.step == "deps" and "incus_timeout" in e.value.detail


def test_abbruch_von_aussen_wird_nicht_wiederholt(sc):
    sc.plan["deps"] = [asyncio.CancelledError()]
    with pytest.raises(asyncio.CancelledError):
        setup()
    assert sc.calls["deps"] == 1


def test_fehlerdetail_enthaelt_die_letzten_zeilen(sc):
    out = "\n".join(f"Zeile {i}" for i in range(100))
    sc.plan["deps"] = [(1, out, "ERR letzte Meldung")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "ERR letzte Meldung" in e.value.detail and "Zeile 99" in e.value.detail and "Zeile 1\n" not in e.value.detail


def test_fehlerdetail_ist_gekuerzt(sc):
    sc.plan["deps"] = [(1, "x" * 50_000, "")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert len(e.value.detail) <= provision.MAX_DETAIL


def test_fehlerdetail_ohne_steuerzeichen(sc):
    sc.plan["deps"] = [(1, "\x1b[31mrot\x1b[0m\x00\x07", "")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "\x1b" not in e.value.detail and "\x00" not in e.value.detail and "rot" in e.value.detail


def test_fehlerdetail_ist_vom_letzten_versuch(sc):
    sc.plan["deps"] = [(1, "", "erster"), (1, "", "zweiter"), (1, "", "dritter")]
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "dritter" in e.value.detail and "erster" not in e.value.detail


def test_lokaler_fehler_hat_auch_ein_detail(sc):
    sc.plan["git"] = [(128, "", "fatal: nicht erlaubt")]
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "fatal: nicht erlaubt" in e.value.detail


def test_detail_enthaelt_keinen_token_oder_projektnamen(sc):
    sc.plan["deps"] = [(1, "", "fehler")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "hh-vibe" not in e.value.detail


def test_start_at_wiederholt_trotzdem(sc):
    sc.plan["deps"] = [FAIL]
    run(provision.setup("p1", lambda _k: None, start_at="deps"))
    assert sc.calls["deps"] == 2 and "user" not in sc.calls


def test_report_wird_je_schritt_nur_einmal_gerufen(sc):
    sc.plan["deps"] = [FAIL, FAIL]
    seen: list[str] = []
    run(provision.setup("p1", seen.append))
    assert seen.count("deps") == 1


def test_detail_nennt_den_containernamen_nicht(sc):
    """Der Name enthält die Projekt-ID; er soll nicht in einer Meldung an die Oberfläche stehen."""
    sc.plan["deps"] = [(1, "", "Error: Instance hh-vibe-01a1abc-def not found")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert "hh-vibe-" not in e.value.detail and "01a1abc-def" in e.value.detail and "not found" in e.value.detail


def test_detail_hat_hoechstens_acht_zeilen(sc):
    """Die Oberfläche zeigt einen Hinweis, kein ganzes Protokoll."""
    sc.plan["deps"] = [(1, "\n".join(f"z{i}" for i in range(500)), "")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert len(e.value.detail.splitlines()) == 8 and e.value.detail.splitlines()[-1] == "z499"


def test_detail_leere_zeilen_zaehlen_nicht(sc):
    sc.plan["deps"] = [(1, "a\n\n\n\nb\n\n", "")] * 3
    with pytest.raises(provision.SetupError) as e:
        setup()
    assert e.value.detail == "a\nb"
