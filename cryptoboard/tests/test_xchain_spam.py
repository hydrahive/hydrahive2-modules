"""xchain_spam — reine Funktion, drei Gründe, echte USDC niemals Spam."""
from __future__ import annotations

from backend import xchain_spam as spam

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
FAKE_CONTRACT = "0x" + "9" * 40


def test_symbol_nicht_ascii_unicode_fake():
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "ꓴ឵ՏᎠ឵Ⲧ", "Fake USDT", resolved=False)
    assert reason == "symbol_nicht_ascii"


def test_url_im_symbol():
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "www.afomo.top ✅", "Claim now", resolved=False)
    # Symbol selbst ist schon nicht-ascii-sauber (Leerzeichen/Emoji) -> greift Regel 1 ODER 2,
    # beide sind in diesem Fall Spam-Gruende; wir pruefen nur: Spam, nicht welcher der beiden.
    assert reason in {"symbol_nicht_ascii", "url_im_namen"}


def test_url_im_namen_reines_ascii_symbol():
    """Symbol selbst ist ASCII-sauber, aber der NAME enthaelt eine URL -> Regel 2 explizit."""
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "CLAIM", "visit www.claim-airdrop.xyz now",
                                     resolved=False)
    assert reason == "url_im_namen"


def test_unbekannter_token_weder_kontrakt_noch_coingecko():
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "XYZ", "Unknown Token", resolved=False)
    assert reason == "unbekannter_token"


def test_echte_usdc_ist_nie_spam():
    reason = spam.classify_incoming("base", USDC_BASE, "USDC", "USD Coin", resolved=True)
    assert reason is None


def test_echte_usdc_ist_nie_spam_auch_bei_seltsamem_namen_weil_kontrakt_entscheidet():
    """Selbst wenn jemand Symbol/Name manipuliert haette -- der KONTRAKT entscheidet.
    (Simulation: known_token() ist nur ueber den Kontrakt definiert, Name/Symbol sind hier egal.)"""
    reason = spam.classify_incoming("base", USDC_BASE, "not-ascii-§§§", "http://evil.example", resolved=False)
    assert reason is None


def test_fake_usdc_token_auf_fremdem_kontrakt_ist_spam_wenn_unresolved():
    """Fake-Token TRAEGT das Symbol 'USDC', sitzt aber auf einem ANDEREN (unbekannten) Kontrakt."""
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "USDC", "USD Coin", resolved=False)
    assert reason == "unbekannter_token"


def test_bekanntes_symbol_aber_resolved_ist_kein_spam():
    """Unbekannter Kontrakt, aber CoinGecko konnte ihn aufloesen (resolved=True) -> kein Spam."""
    reason = spam.classify_incoming("base", FAKE_CONTRACT, "SOMECOIN", "Some Coin", resolved=True)
    assert reason is None


def test_is_spam_wrapper():
    assert spam.is_spam("base", FAKE_CONTRACT, "ꓴ឵ՏᎠ឵Ⲧ", "x", resolved=False) is True
    assert spam.is_spam("base", USDC_BASE, "USDC", "USD Coin", resolved=True) is False
