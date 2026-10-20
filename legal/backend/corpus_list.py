"""Kernliste der Gesetze (legal/SPEC-LEGAL.md §4.1, Till 20.10.2026). Alle Kürzel gegen gii-toc.xml geprüft."""
from __future__ import annotations

CORE: dict[str, tuple[str, ...]] = {
    "Zivil- und Verfahrensrecht": ("bgb", "bgbeg", "zpo", "gvg", "rvg", "gkg_2004", "uwg_2004", "vvg_2008", "pflvg"),
    "Wohnen und Immobilien": ("betrkv", "heizkostenv", "woflv", "woeigg", "gbo", "bbaug", "erbbauv", "grestg_1983",
                              "beurkg"),
    "Familie": ("famfg", "famgkg", "versausglg", "gewschg", "lpartg", "bkgg_1996", "beeg", "uhvorschg",
                "erbstg_1974"),
    "Sozialrecht": ("sgb_1", "sgb_2", "sgb_5", "sgb_8", "sgb_10", "sgb_11", "sgb_12"),
    "Verwaltung": ("vwvfg", "vwgo"),
    "Strafrecht und Bußgeld": ("stgb", "stpo", "owig_1968", "jgg", "btmg_1981", "stvo_2013", "stvg"),
    "Arbeit, Steuer, Daten": ("burlg", "kschg", "arbzg", "estg", "bdsg_2018", "tkg_2021", "ttdsg", "ddg"),
    "Grundlagen": ("gg", "rdg", "urhg"),
}


def core_keys() -> list[str]:
    return [k for keys in CORE.values() for k in keys]


def group_of(key: str) -> str | None:
    return next((g for g, keys in CORE.items() if key in keys), None)
