"""S7: reine Bluetooth-Logik – Adresse, Art, Signal, Zwillinge (BT3.0/BT4.0), Sortierung, schwacher Empfang."""
from __future__ import annotations

import pytest

from renderer import bt_model as m


# --- Adresse -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw, ok", [
    ("B4:EE:25:ED:70:7F", "B4:EE:25:ED:70:7F"),
    ("b4:ee:25:ed:70:7f", "B4:EE:25:ED:70:7F"),           # Kleinschreibung wird groß
    (" B4:EE:25:ED:70:7F ", None),                         # kein Trimmen – genau das Format
    ("B4:EE:25:ED:70", None),
    ("B4:EE:25:ED:70:7F:00", None),
    ("B4-EE-25-ED-70-7F", None),
    ("G4:EE:25:ED:70:7F", None),
    ("../etc/passwd", None),
    ("", None),
    (None, None),
    (12, None),
])
def test_adresse(raw, ok):
    assert m.address(raw) == ok


# --- Art + Signal --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("icon, art", [
    ("input-keyboard", "keyboard"), ("input-mouse", "mouse"), ("input-tablet", "mouse"),
    ("audio-headset", "headphones"), ("audio-headphones", "headphones"), ("audio-card", "speaker"),
    ("phone", "phone"), ("computer", "other"), (None, "other"), ("", "other"),
])
def test_art(icon, art):
    assert m.kind(icon) == art


@pytest.mark.parametrize("rssi, stufe", [
    (None, 0), (-110, 1), (-91, 1), (-90, 2), (-76, 2), (-75, 3), (-61, 3), (-60, 4), (-30, 4),
])
def test_signal_stufe(rssi, stufe):
    assert m.bars(rssi) == stufe


# --- Geräteliste ---------------------------------------------------------------------------------------------------
def dev(addr, name=None, *, typ="public", rssi=-60, paired=False, connected=False, icon="input-keyboard", le=False):
    return {"address": addr, "address_type": typ, "name": name, "rssi": rssi, "paired": paired,
            "connected": connected, "icon": icon, "le": le}


RAPOO_BT3 = dev("B4:EE:25:ED:70:7F", "RAPOO BT3.0 KB", rssi=-62)
RAPOO_BT4 = dev("B4:EE:25:EE:72:7F", "RAPOO BT4.0 KB", rssi=-58, le=True)


def test_zwillinge_werden_eine_zeile_klassisch_zuerst():
    rows = m.rows([RAPOO_BT4, RAPOO_BT3])
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "RAPOO KB"
    assert r["addresses"] == ["B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"]      # klassisch vor LE
    assert r["rssi"] == -58                                                 # stärkstes Signal
    assert r["kind"] == "keyboard"


def test_aehnlicher_name_anderer_hersteller_bleibt_getrennt():
    fremd = dev("11:22:33:EE:72:7F", "RAPOO BT4.0 KB", le=True)
    assert len(m.rows([RAPOO_BT3, fremd])) == 2


def test_gleicher_hersteller_anderer_name_bleibt_getrennt():
    maus = dev("B4:EE:25:00:00:01", "RAPOO BT3.0 MOUSE", icon="input-mouse")
    assert len(m.rows([RAPOO_BT3, maus])) == 2


def test_zwilling_gekoppelt_wenn_einer_gekoppelt():
    rows = m.rows([dict(RAPOO_BT3, paired=True, connected=True), RAPOO_BT4])
    assert rows[0]["paired"] is True and rows[0]["connected"] is True


def test_name_fehlt_unbekannt_und_name_wird_gekuerzt():
    rows = m.rows([dev("AA:BB:CC:00:00:01", None), dev("AA:BB:CC:00:00:02", "x" * 200)])
    names = sorted(r["name"] for r in rows)
    assert "Unbekanntes Gerät" in names
    assert max(len(n) for n in names) == 60


def test_sortierung_gekoppelt_vor_signal():
    nah = dev("AA:00:00:00:00:01", "Nah", rssi=-40)
    gekoppelt = dev("AA:00:00:00:00:02", "Alt", rssi=-80, paired=True)
    fern = dev("AA:00:00:00:00:03", "Fern", rssi=-85)
    assert [r["name"] for r in m.rows([fern, nah, gekoppelt])] == ["Alt", "Nah", "Fern"]


def test_weitere_geraete_ohne_namen_und_schwach():
    leer_schwach = dev("AA:00:00:00:00:04", None, rssi=-95)
    leer_stark = dev("AA:00:00:00:00:05", None, rssi=-60)
    mit_namen_schwach = dev("AA:00:00:00:00:06", "Box", rssi=-95)
    rows = {r["addresses"][0]: r for r in m.rows([leer_schwach, leer_stark, mit_namen_schwach])}
    assert rows["AA:00:00:00:00:04"]["more"] is True
    assert rows["AA:00:00:00:00:05"]["more"] is False
    assert rows["AA:00:00:00:00:06"]["more"] is False


def test_schwacher_empfang():
    assert m.weak_signal([dev("AA:00:00:00:00:01", "a", rssi=-102), dev("AA:00:00:00:00:02", "b", rssi=-98)]) is True
    assert m.weak_signal([dev("AA:00:00:00:00:01", "a", rssi=-102), dev("AA:00:00:00:00:02", "b", rssi=-56)]) is False
    assert m.weak_signal([]) is False                                    # nichts gesehen ist kein Empfangsproblem
    assert m.weak_signal([dev("AA:00:00:00:00:01", "a", rssi=None)]) is False


def test_pair_reihenfolge_ist_die_zeile():
    """Gekoppelt wird in Reihenfolge der Adressen (klassisch zuerst) – der Dienst nimmt rows()[i]['addresses']."""
    assert m.pair_order([RAPOO_BT4, RAPOO_BT3], "B4:EE:25:EE:72:7F") == ["B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"]
    assert m.pair_order([RAPOO_BT3], "B4:EE:25:ED:70:7F") == ["B4:EE:25:ED:70:7F"]
    assert m.pair_order([RAPOO_BT3], "AA:AA:AA:AA:AA:AA") == []           # nicht gesehen
