"""Atelier — Video-Poll-Timeout ist dauer-abhängig (Fix: Sora 2 Pro 20s
brach nach fester 7,5-min-Grenze ab, obwohl das Video noch generierte)."""
from __future__ import annotations

from backend import video


def test_timeout_waechst_mit_dauer():
    t5 = video._poll_timeout_for(5)
    t20 = video._poll_timeout_for(20)
    assert t20 > t5
    # 20s bekommt jetzt deutlich mehr als die alte 7,5-min-Grenze (450s)
    assert t20 > 450.0


def test_timeout_basis_schon_ueber_alter_grenze():
    # selbst der kürzeste Clip hat mehr Budget als früher (7,5 min)
    assert video._poll_timeout_for(1) > 450.0


def test_timeout_gedeckelt():
    # sehr lange Clips laufen nicht unbegrenzt
    assert video._poll_timeout_for(9999) == video._POLL_TIMEOUT_CAP


def test_timeout_robust_gegen_muell():
    # ungültige Dauer → Fallback (kein Crash)
    assert video._poll_timeout_for("x") == video._poll_timeout_for(5)
    assert video._poll_timeout_for(None) == video._poll_timeout_for(5)
    assert video._poll_timeout_for(0) == video._poll_timeout_for(1)  # min 1s
