"""E2: Aussehen prüfen und als Theme (config.json) für cleanyourtv ausgeben; Skripte zum Schieben."""
from __future__ import annotations

import json

import pytest
from backend import apps, look, theme_push

S = "192.168.178.200:5555"


def test_standard():
    v = look.clean({})
    assert v == look.DEFAULT


def test_eingaben_werden_geprueft_und_unbekanntes_verworfen():
    v = look.clean({"columns": 4, "dock": ["com.plexapp.android", "com.netflix.ninja", "com.plexapp.android"],
                    "labels": {"de.prosiebensat1digital.seventv": "Joyn", "com.netflix.ninja": "  "},
                    "background_color": "#1A2B3C", "boese": "rm -rf /"})
    assert v["columns"] == 4 and v["dock"] == ["com.plexapp.android", "com.netflix.ninja"]
    assert v["labels"] == {"de.prosiebensat1digital.seventv": "Joyn"} and v["background_color"] == "#1a2b3c"
    assert "boese" not in v


@pytest.mark.parametrize("feld,wert", [("columns", 0), ("columns", 9), ("columns", True), ("rows_below_dock", 4),
                                       ("wallpaper_dim", 91), ("dock_opacity", 29), ("rotation_minutes", 1441),
                                       ("background_color", "red"), ("clock_format", "13"), ("show_greeting", "ja"),
                                       ("dock", ["kein paket"]), ("dock", "com.a.b"), ("hidden", ["com.a.b; reboot"]),
                                       ("labels", {"com.a.b": "x" * 25}), ("labels", {"kaputt": "x"}),
                                       ("greeting_name", "a\nb"), ("dock", [f"com.a.b{i}" for i in range(61)])])
def test_ungueltig(feld, wert):
    with pytest.raises(look.TvwLookError) as e:
        look.clean({feld: wert})
    assert (e.value.code, e.value.field) == ("tvw_look_invalid", feld)


def test_theme_ohne_bilder():
    cfg = look.theme_config(look.clean({"dock": ["com.plexapp.android"], "hidden": ["com.sony.dtv.timers"],
                                        "labels": {"com.netflix.ninja": "Filme"}, "columns": 5}), {})
    assert cfg["dock_apps"] == ["com.plexapp.android"] and cfg["fill_dock"] is False
    assert cfg["hidden_apps"] == ["com.sony.dtv.timers"] and cfg["app_labels"] == ["com.netflix.ninja=Filme"]
    assert cfg["columns"] == 5 and cfg["wallpaper"] is False and "wallpaper_moods" not in cfg


def test_theme_leere_leiste_fuellt_selbst():
    assert look.theme_config(look.clean({}), {})["fill_dock"] is True


def test_theme_mit_bildern_je_tageszeit():
    cfg = look.theme_config(look.clean({"wallpaper_dim": 30, "rotation_minutes": 60}),
                            {"morning": ["morning-a.jpg"], "night": ["night-b.jpg", "night-c.jpg"]})
    assert cfg["wallpaper"] is True and cfg["wallpaper_dim"] == 30 and cfg["wallpaper_rotation_minutes"] == 60
    assert cfg["wallpaper_moods"] == {"morning": ["morning-a.jpg"],
                                      "evening": ["morning-a.jpg", "night-b.jpg", "night-c.jpg"],
                                      "night": ["night-b.jpg", "night-c.jpg"]}


def test_theme_ein_bild_ohne_tageszeiten():
    cfg = look.theme_config(look.clean({}), {"morning": ["morning-a.jpg"]})
    assert cfg["wallpaper"] is True and "wallpaper_moods" not in cfg


def test_theme_json_ist_gueltig():
    assert json.loads(look.theme_json(look.clean({"greeting_name": "Till"}), {}))["greeting_name"] == "Till"


# --- Schieben -------------------------------------------------------------------------------------------------

def test_schieben_nur_erlaubte_dateinamen():
    for bad in ([], ["wallpapers/a.jpg"], ["config.json", "../x.jpg"], ["config.json", "wallpapers/A B.jpg"],
                ["config.json", "wallpapers/x.png"]):
        with pytest.raises(ValueError):
            theme_push.push_script(S, bad)


def test_schieben_reihenfolge_und_nur_app_ordner():
    s = theme_push.push_script(S, ["config.json", "wallpapers/morning-abc.jpg"], revision="r1")
    assert s.index('[ "$st" = device ] || exit 0') < s.index("rm -f /sdcard")
    assert s.index("push /home/ubuntu/theme/config.json") < s.index("theme_revision") < s.index("am force-stop")
    assert "content write --uri content://com.gathin.tvhome.theme/wallpapers/morning-abc.jpg" in s
    for verboten in ("pm uninstall", "pm disable", "settings put", "reboot", "rm -rf"):
        assert verboten not in s
    for pfad in [x for x in s.split() if x.startswith("/sdcard")]:
        assert pfad.startswith("/sdcard/Android/data/com.gathin.tvhome/files"), pfad


def test_fehlende_dateien_erkannt():
    assert theme_push.check("__TVW__ state=device\ntvw-not-written wallpapers/a.jpg\n") == ["wallpapers/a.jpg"]
    assert theme_push.check("__TVW__ state=device\n__TVW__ restarted\n") == []


# --- Apps lesen -----------------------------------------------------------------------------------------------

def test_app_liste_lesen():
    out = ("__TVW__ state=device\n__TVW__ pkg com.netflix.ninja 50157\n__TVW__ pkg kaputt 1\n"
           "__TVW__ pkg com.plexapp.android x\n__TVW__ pkg tv.emby.embyatv 2010\n")
    assert apps.parse_list(out) == {"com.netflix.ninja": "50157", "tv.emby.embyatv": "2010"}


def test_lese_skript_nur_gepruefte_pakete():
    s = apps.read_script(S, ["com.netflix.ninja", "x; reboot"])
    assert "com.netflix.ninja" in s and "reboot" not in s
    for verboten in ("pm uninstall", "pm disable", "pm install", "settings put"):
        assert verboten not in s


def test_bilder_werden_geprueft_und_eingepasst(tmp_path, monkeypatch):
    import io
    import tarfile

    from PIL import Image
    monkeypatch.setattr(apps, "image_dir", lambda d: tmp_path / d)
    ok = io.BytesIO()
    Image.new("RGB", (640, 360), (229, 9, 20)).save(ok, "PNG")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, data in (("./com.netflix.ninja.img", ok.getvalue()), ("./com.kaputt.app.img", b"kein bild"),
                           ("./../boese.img", ok.getvalue())):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    colors = apps.store_images("d1", buf.getvalue())
    assert colors == {"com.netflix.ninja": "#e50914"}
    assert sorted(p.name for p in (tmp_path / "d1").iterdir()) == ["com.netflix.ninja.png"]
    with Image.open(tmp_path / "d1" / "com.netflix.ninja.png") as im:
        assert im.size == (apps.IMG_W, apps.IMG_H)
