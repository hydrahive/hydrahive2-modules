"""Entrümpeln Teil 1 (backend/debloat.py): Listen lesen, Profil zuordnen, Empfehlung und Schutz. Erfundene Listen."""
from __future__ import annotations

from backend import debloat, guard

TCL_LIST = """# TCL Beispiel 55X (product G08_4K_GB, device G08), Google TV 14, firmware UTT2.250416.001 AU02.
#
# Left enabled on purpose: com.tcl.tv, com.tcl.ttvs (also the firmware updater), com.tcl.suspension (the input
# list) and every streaming app.
#
# Note on something else entirely: com.tcl.other.mention is only talked about here.

# TCL pushes and demo
com.tcl.dashboard           # TCL Home panel and its promotions
com.tcl.exhibit             # store demo mode

# Telemetry
com.tcl.logkit              # log capture service
# com.tcl.gamebar
com.android.adservices.api

# Replaced by the custom launcher
com.google.android.apps.tv.launcherx
com.google.android.tungsten.setupwraith  # setup wizard
"""
OTHER_TCL = """# TCL Android 11 (G03), firmware RTM.220101 AA01
com.tcl.dashboard   # promos
com.tcl.guard
"""
SONY = """# Sony KD-1 (BRAVIA_ATV3_4K), build PTT1.190515.001.S54
com.sony.dtv.sonyselect   # ad tile
com.tcl.logkit
"""
ID_TCL = {"brand": "TCL", "product": "G08_4K_GB", "device": "G08", "model": "Smart TV Pro",
          "build_id": "UTT2.250416.001", "incremental": "AU02"}
GTV = "com.google.android.apps.tv.launcherx"


def lists() -> dict:
    out = {}
    for name, text, brand in (("tcl-a/debloat.txt", TCL_LIST, "TCL"), ("tcl-b/debloat.txt", OTHER_TCL, "TCL"),
                              ("sony-a/debloat.txt", SONY, "Sony")):
        off, kept, head = debloat.read_list(text)
        out[name] = {"off": off, "kept": kept, "head": head, "brand": brand}
    return out


def test_liste_lesen_gruppen_notizen_angelassen():
    off, kept, head = debloat.read_list(TCL_LIST)
    assert [p for p, _, _ in off] == ["com.tcl.dashboard", "com.tcl.exhibit", "com.tcl.logkit",
                                      "com.android.adservices.api", GTV, guard.SETUP]
    assert dict((p, g) for p, _, g in off)["com.tcl.exhibit"] == "TCL pushes and demo"
    assert dict((p, g) for p, _, g in off)["com.android.adservices.api"] == "Telemetry"
    assert dict((p, n) for p, n, _ in off)["com.tcl.logkit"] == "log capture service"
    assert kept == {"com.tcl.tv", "com.tcl.ttvs", "com.tcl.suspension", "com.tcl.gamebar"}
    assert "com.tcl.other.mention" not in kept and "UTT2.250416.001" in head


def test_crlf_und_bom_egal():
    off, _, _ = debloat.read_list("\ufeff" + TCL_LIST.replace("\n", "\r\n"))
    assert len(off) == 6


def test_passende_listen_nach_build_und_produkt():
    assert debloat.peers(lists(), ID_TCL) == (["tcl-a/debloat.txt"], 70)   # Build, Stand, Produkt, Gerät


def test_fremde_marke_und_zu_schwach_keine_liste():
    assert debloat.peers(lists(), {**ID_TCL, "brand": "Hisense"}) == ([], 0)
    assert debloat.peers(lists(), {"brand": "TCL", "model": "Smart TV Pro"}) == ([], 0)


def test_kernschutz_wie_cleanyourtv():
    for p in ("android", "com.android.systemui", "com.android.tv.settings", "com.android.providers.media",
              "com.google.android.permissioncontroller", "com.android.location.fused", "com.mediatek.tv.service"):
        assert debloat.is_core(p), p
    for p in ("com.android.providers.calendar", "com.tcl.dashboard", "com.android.adservices.api"):
        assert not debloat.is_core(p), p


def test_auswertung_tcl():
    pk = {"com.tcl.dashboard": "on", "com.tcl.exhibit": "off", "com.tcl.logkit": "on", "com.tcl.ttvs": "on",
          "com.tcl.guard": "on", GTV: "off", guard.SETUP: "off", "com.android.systemui": "on",
          "com.netflix.ninja": "on", "com.android.adservices.api": "on"}
    v = debloat.evaluate(pk, lists(), ID_TCL, GTV)
    rows = {r["package"]: r for r in v["packages"]}
    assert v["lists_used"] == ["tcl-a/debloat.txt"] and v["total_lists"] == 3
    assert "com.netflix.ninja" not in rows and "com.android.systemui" not in rows      # keine Liste kennt sie
    assert {k: rows["com.tcl.dashboard"][k] for k in ("recommended", "of", "lists", "locked", "group", "note")} == {
        "recommended": True, "of": 1, "lists": 2, "locked": "", "group": "ads", "note": "TCL Home panel and its promotions"}
    assert rows["com.tcl.logkit"]["group"] == "tracking" and rows["com.tcl.exhibit"]["group"] == "demo"
    assert "com.tcl.guard" not in rows                         # nur eine fremde Liste, an → nicht gezeigt
    assert rows[GTV]["locked"] == "home" and rows[guard.SETUP]["locked"] == "home"
    assert "com.tcl.ttvs" not in rows
    assert v["off_count"] == 3 and v["recommended_on"] == 3
    assert [r["recommended"] for r in v["packages"]] == sorted((r["recommended"] for r in v["packages"]), reverse=True)


def _peer(name: str, off: list[str], kept: set[str] = frozenset()) -> tuple[str, dict]:
    return name, {"off": [(p, "", "Extras") for p in off], "kept": set(kept), "brand": "TCL",
                  "head": "UTT2.250416.001 AU02 G08_4K_GB G08"}


def test_mehrheit_statt_vorliebe_eines_besitzers():
    ls = dict([_peer("a/debloat.txt", ["com.tcl.logkit", "com.netflix.ninja"]),
               _peer("b/debloat.txt", ["com.tcl.logkit"], {"com.netflix.ninja"}),
               _peer("c/debloat.txt", ["com.tcl.logkit", "com.tcl.ttvs"], {"com.tcl.ttvs"})])
    pk = {"com.tcl.logkit": "on", "com.netflix.ninja": "on", "com.tcl.ttvs": "on"}
    rows = {r["package"]: r for r in debloat.evaluate(pk, ls, ID_TCL, GTV)["packages"]}
    assert rows["com.tcl.logkit"]["recommended"] and rows["com.tcl.logkit"]["of"] == 3
    assert not rows["com.netflix.ninja"]["recommended"] and rows["com.netflix.ninja"]["kept"] == 1
    assert not rows["com.tcl.ttvs"]["recommended"]


def test_mehrheit_aber_eine_liste_laesst_es_bewusst_an_umstritten():
    ls = dict([_peer("a/debloat.txt", ["com.tcl.ttvs"]), _peer("b/debloat.txt", ["com.tcl.ttvs"]),
               _peer("c/debloat.txt", [], {"com.tcl.ttvs"})])
    row = debloat.evaluate({"com.tcl.ttvs": "on"}, ls, ID_TCL, GTV)["packages"][0]
    assert (row["recommended"], row["of"], row["kept"]) == (False, 2, 1)


def test_genau_die_haelfte_reicht_nicht():
    ls = dict([_peer("a/debloat.txt", ["com.tcl.guard"]), _peer("b/debloat.txt", [])])
    rows = debloat.evaluate({"com.tcl.guard": "on"}, ls, ID_TCL, GTV)["packages"]
    assert rows[0]["recommended"] is False and rows[0]["of"] == 1


def test_ohne_passende_liste_nichts_empfohlen():
    v = debloat.evaluate({"com.tcl.dashboard": "on", "com.tcl.exhibit": "off"}, lists(), {"brand": "Philips"}, "")
    assert v["lists_used"] == [] and [r["package"] for r in v["packages"]] == ["com.tcl.exhibit"]
    assert v["packages"][0]["recommended"] is False


def test_gruppen():
    assert debloat.group_of("Samba TV ACR viewing tracker tv.samba.ssm") == "tracking"
    assert debloat.group_of("Sony and Google content, ads and promos") == "ads"
    assert debloat.group_of("Retail demo com.sony.dtv.demomode") == "demo"
    assert debloat.group_of("Preloaded help apps manual") == "help"
    assert debloat.group_of("something com.example.thing") == "other"
