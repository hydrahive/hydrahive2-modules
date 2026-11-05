"""Baustein 6: Kostengrenze des Heilungslaufs (an hydratest 5.11. gefunden).

Die Heilung läuft in der Sitzung des Chats. Der Verbrauch davor gehört nicht zum Lauf: Ein langer Chat darf die Heilung
nicht schon vor Runde 1 sperren (gemessen: Grenze 4000, „letzte Runde“ aus dem Chat 13 426 → Lauf nach 0 Tokens aus).
"""
from __future__ import annotations

from backend import heal_run


def row(p=0, c=0, cc=0, out=0):
    return {"prompt_tokens": p, "cache_read_tokens": c, "cache_creation_tokens": cc, "completion_tokens": out}


def over(rows, before_n, limit):
    return heal_run.over_limit(rows, before_n, limit)


def test_vor_runde_eins_nie_ueber_der_grenze_auch_bei_langem_chat():
    chat = [row(p=90_000, out=3_000)] * 5
    assert over(chat, len(chat), 4_000) is False


def test_nach_runde_eins_zaehlt_nur_der_lauf():
    chat = [row(p=90_000)] * 3
    run1 = [row(p=1_000, out=200)]
    assert over(chat + run1, len(chat), 4_000) is False          # 1 200 + nächste ~1 200 = 2 400 < 4 000


def test_naechste_runde_wird_vorab_mitgerechnet():
    run = [row(p=1_500, out=500), row(p=1_800, out=300)]          # verbraucht 4 100, letzte 2 100
    assert over(run, 0, 6_000) is True                            # 4 100 + 2 100 > 6 000
    assert over(run, 0, 7_000) is False


def test_genau_auf_der_grenze_ist_noch_erlaubt():
    run = [row(p=1_000, out=1_000)]
    assert over(run, 0, 4_000) is False                           # 2 000 + 2 000 == 4 000 → nicht darüber


def test_cache_tokens_zaehlen_mit():
    run = [row(p=100, c=3_000, cc=500, out=100)]
    assert over(run, 0, 3_000) is True                            # 3 700 verbraucht


def test_ohne_grenze_nie():
    assert over([row(p=10**9)], 0, 0) is False


def test_leere_zeilen_und_none_werte():
    assert over([{"prompt_tokens": None, "cache_read_tokens": None, "cache_creation_tokens": None,
                  "completion_tokens": None}], 0, 100) is False


def test_verbrauch_des_laufs_ohne_chat_davor():
    chat = [row(p=50_000)] * 2
    run = [row(p=700, out=100), row(p=900, out=100)]
    assert heal_run.spent(chat + run, len(chat)) == 1_800
