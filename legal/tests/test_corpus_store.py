"""Gesetz speichern: Hash-Vergleich, alte Fassung bleibt mit valid_to erhalten (Spec §4.1)."""
from __future__ import annotations

from backend import corpus_store as store
from backend.gii_parse import parse_law
from conftest import fixture_xml


def _save(key="bgb", xml=None, at="2026-10-20T03:30:00Z", pinned=True):
    xml = xml if xml is not None else fixture_xml(key)
    return store.save_law(parse_law(key, xml), xml, fetched_at=at, pinned=pinned)


def test_first_import_stores_law_and_norms():
    """Fixture: 7 BGB-Normen (§ 10 weggefallen und Inhaltsübersicht zählen nicht)."""
    res = _save()
    assert res == {"key": "bgb", "changed": True, "norms": 7}
    law = store.get_law("bgb")
    assert law["abbr"] == "BGB" and law["pinned"] is True
    assert store.get_norm("BGB", "§ 536c")["title"].startswith("Während der Mietzeit")


def test_same_hash_changes_nothing():
    _save()
    assert _save(at="2026-10-21T03:30:00Z") == {"key": "bgb", "changed": False, "norms": 7}
    assert store.get_law("bgb")["fetched_at"] == "2026-10-21T03:30:00Z"     # Abruf vermerkt, Inhalt gleich
    assert store.count_norms("BGB", include_old=True) == 7


def test_new_version_keeps_old_text_with_valid_to():
    _save(at="2026-10-20T03:30:00Z")
    changed = fixture_xml("bgb").replace("unverzüglich anzuzeigen".encode(), b"binnen einer Woche anzuzeigen")
    res = _save(xml=changed, at="2026-11-02T03:30:00Z")
    assert res["changed"] is True
    now = store.get_norm("BGB", "§ 536c")
    assert "binnen einer Woche" in now["text"] and now["valid_from"] == "2026-11-02T03:30:00Z"
    old = store.get_norm("BGB", "§ 536c", as_of="2026-10-25T00:00:00Z")
    assert "unverzüglich" in old["text"] and old["valid_to"] == "2026-11-02T03:30:00Z"
    assert store.count_norms("BGB") == 7                                    # gültige Fassung zählt einmal


def test_norm_removed_in_new_version_is_closed_not_deleted():
    _save()
    without = fixture_xml("bgb").replace("<enbez>§ 1601</enbez>".encode(), "<enbez>§ 1601x</enbez>".encode())
    _save(xml=without, at="2026-11-02T03:30:00Z")
    assert store.get_norm("BGB", "§ 1601") is None
    assert store.get_norm("BGB", "§ 1601", as_of="2026-10-25T00:00:00Z") is not None


def test_unknown_norm_is_none():
    _save()
    assert store.get_norm("BGB", "§ 99999") is None
    assert store.get_norm("XYZ", "§ 1") is None


def test_known_abbrs_lists_loaded_laws():
    _save("bgb")
    _save("owig_1968")
    assert {"BGB", "OWiG"} <= store.known_abbrs()
