"""Störungen aus Ereignissen der Dream Machine und aus der eigenen Minuten-Messung."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend import outages

TZ = ZoneInfo("Europe/Berlin")


def ts(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp())


def test_aus_wiederkehr_mit_dauer_wird_zeitraum():
    ev = [{"kind": "wan_restored", "ts": ts("2026-10-27 22:47"), "duration_s": 30660},
          {"kind": "wan_failed", "ts": ts("2026-10-27 14:17"), "duration_s": None},
          {"kind": "wan_blip", "ts": ts("2026-10-27 22:56"), "duration_s": 24},
          {"kind": "wan_flapping", "ts": ts("2026-10-27 22:56"), "duration_s": 30000}]
    got = outages.from_udm(ev)
    assert {"start": ts("2026-10-27 22:47") - 30660, "end": ts("2026-10-27 22:47"), "kind": "wan", "source": "udm"} in got
    assert {"start": ts("2026-10-27 22:56") - 24, "end": ts("2026-10-27 22:56"), "kind": "blip", "source": "udm"} in got
    assert len(got) == 2


def test_minuten_ohne_internet_und_ohne_kabel():
    t0 = ts("2026-11-02 10:00")
    paths = ["cable", "none", "none", "mobile", "mobile", "cable", "unknown", "none"]
    samples = [{"ts": t0 + i * 60, "path": p} for i, p in enumerate(paths)]
    got = outages.from_samples(samples)
    inet = [o for o in got if o["kind"] == "internet"]
    cable = [o for o in got if o["kind"] == "cable"]
    assert inet == [{"start": t0 + 60, "end": t0 + 180, "kind": "internet", "source": "probe"},
                    {"start": t0 + 420, "end": t0 + 480, "kind": "internet", "source": "probe"}]
    assert cable == [{"start": t0 + 60, "end": t0 + 300, "kind": "cable", "source": "probe"},
                     {"start": t0 + 420, "end": t0 + 480, "kind": "cable", "source": "probe"}]


def test_luecke_in_der_messung_trennt():
    t0 = ts("2026-11-02 10:00")
    samples = [{"ts": t0, "path": "none"}, {"ts": t0 + 600, "path": "none"}]
    got = [o for o in outages.from_samples(samples) if o["kind"] == "internet"]
    assert len(got) == 2 and got[0]["end"] == t0 + 60


def test_zusammenfassen_ueberlappend():
    a = {"start": 0, "end": 100, "kind": "wan", "source": "udm"}
    b = {"start": 50, "end": 200, "kind": "wan", "source": "udm"}
    c = {"start": 300, "end": 400, "kind": "wan", "source": "udm"}
    d = {"start": 60, "end": 70, "kind": "blip", "source": "udm"}
    got = outages.merge([c, b, a, d])
    assert {"start": 0, "end": 200, "kind": "wan", "source": "udm"} in got
    assert c in got and d in got and len(got) == 3


def test_pro_tag_ueber_mitternacht():
    o = [{"start": ts("2026-10-27 22:00"), "end": ts("2026-10-28 03:00"), "kind": "wan", "source": "udm"},
         {"start": ts("2026-10-28 10:00"), "end": ts("2026-10-28 10:30"), "kind": "wan", "source": "udm"},
         {"start": ts("2026-10-28 11:00"), "end": ts("2026-10-28 11:10"), "kind": "blip", "source": "udm"}]
    got = outages.per_day(o, "wan", TZ)
    assert got == {"2026-10-27": 7200, "2026-10-28": 3 * 3600 + 1800}


def test_pro_tag_zeitumstellung():
    # 25.10.2026 hat 25 Stunden (Winterzeit) – ganzer Tag aus = 90000 s
    o = [{"start": ts("2026-10-25 00:00"), "end": ts("2026-10-26 00:00"), "kind": "wan", "source": "udm"}]
    assert outages.per_day(o, "wan", TZ) == {"2026-10-25": 90000}
