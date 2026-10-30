"""Sony-Client gegen den nachgebauten Fernseher (Werte wie am echten Gerät gemessen)."""
from __future__ import annotations

import pytest
from backend import client
from conftest import CHANNELS, PSK


async def test_status_liest_alles(configured):
    s = await client.status()
    assert s == {"power": "on", "channel": {"number": 6, "name": "SAT.1"}, "program": "Sendung SAT.1",
                 "volume": 14, "muted": False, "output": "speaker", "model": "KD-60XF8305"}


async def test_status_im_standby_ohne_sender(configured):
    """Gemessen 29.10.: im Standby antworten Ton und Sender mit 40005 „Display Is Turned off“ – das ist „aus“."""
    configured.power = "standby"
    s = await client.status()
    assert s == {"power": "standby", "channel": None, "program": "", "volume": None, "muted": None,
                 "output": None, "model": "KD-60XF8305"}
    assert not any(c[1] == "getPlayingContentInfo" for c in configured.calls)


async def test_lautstaerke_im_standby_klarer_fehler(configured):
    configured.power = "standby"
    with pytest.raises(client.TVError) as e:
        await client.set_volume("+1")
    assert e.value.code == "tv_is_off"


async def test_sender_im_standby_klarer_fehler(configured):
    configured.power = "standby"
    with pytest.raises(client.TVError) as e:
        await client.set_channel("ZDF")
    assert e.value.code == "tv_is_off"
    assert not any(c[1] == "setPlayContent" for c in configured.calls)


async def test_schluessel_geht_nur_in_die_kopfzeile(configured):
    await client.status()
    await client.set_channel("ZDF")
    await client.set_volume("+1")
    sent = [c for c in configured.calls if c[1] != "getInterfaceInformation"]
    assert sent and all(c[4].get("X-Auth-PSK") == PSK for c in sent)
    assert all(PSK not in repr(c[2]) for c in configured.calls)         # nie in den Parametern


async def test_senderliste_mit_version_die_der_tv_kann(configured):
    ch = await client.channels()
    assert [c["number"] for c in ch] == [1, 2, 6, 7, 10, 12]
    assert ch[1] == {"number": 2, "name": "ZDF HD", "uri": CHANNELS[1]["uri"]}
    assert {c[3] for c in configured.calls if c[1] == "getContentList"} <= {"1.0", "1.2"}


async def test_senderliste_wird_kurz_gemerkt(configured):
    await client.channels()
    await client.channels()
    assert sum(1 for c in configured.calls if c[1] == "getContentList") == 1


@pytest.mark.parametrize(("query", "number"), [("ZDF", 2), ("zdf hd", 2), ("2", 2), ("Platz 7", 7),
                                               ("kabel 1", 7), ("Kabel Eins", 7), ("sat1", 6), ("Das Erste", 1),
                                               ("ard", 1), ("zdf neo", 12), ("ZDFinfo", 10)])
async def test_sender_finden(configured, query, number):
    assert (await client.find_channel(query))["number"] == number


async def test_sender_unbekannt(configured):
    with pytest.raises(client.TVError) as e:
        await client.find_channel("Bibel TV")
    assert e.value.code == "tv_channel_unknown"


async def test_eindeutiger_anfang_wird_genommen(configured):
    assert (await client.find_channel("zdf i"))["name"] == "ZDFinfo HD"


async def test_sender_mehrdeutig_fragt_nach(configured):
    """„zdfn“ passt nur auf ZDFneo, „zdf“ genau auf ZDF – aber „das“? Hier zwei Sender mit gleichem Anfang."""
    configured_list = [{"number": 20, "name": "Sport1"}, {"number": 21, "name": "Sport1+"},
                       {"number": 22, "name": "Sportdigital"}]
    from backend import matching
    with pytest.raises(client.TVError) as e:
        matching.pick_channel([{**c, "uri": "u"} for c in configured_list], "spor")
    assert e.value.code == "tv_channel_ambiguous" and "Sport1" in str(e.value) and "Sportdigital" in str(e.value)


async def test_umschalten_und_nachlesen(configured):
    s = await client.set_channel("kabel eins")
    assert s["channel"] == {"number": 7, "name": "kabel eins"}
    assert configured.playing["title"] == "kabel eins"


async def test_lautstaerke_absolut_und_relativ(configured):
    assert (await client.set_volume("20"))["volume"] == 20
    assert (await client.set_volume("-5"))["volume"] == 15
    assert (await client.set_volume("+3"))["volume"] == 18


@pytest.mark.parametrize(("start", "value"), [(40, "61"), (40, "100"), (40, "+50"), (40, "-21"), (40, "+21"),
                                              (50, "61"), (55, "+6"), (58, "70"), (62, "+1"), (62, "63")])
async def test_lautstaerke_grenzen(configured, start, value):
    """(50, „61“) und (55, „+6“) reißen nur die Obergrenze 60, nicht die Schritt-Grenze 20."""
    configured.volume = start
    with pytest.raises(client.TVError) as e:
        await client.set_volume(value)
    assert e.value.code == "tv_volume_limit"
    assert configured.volume == start


@pytest.mark.parametrize("value", ["laut", "", "1.5", "++2", "-"])
async def test_lautstaerke_ungueltig(configured, value):
    with pytest.raises(client.TVError) as e:
        await client.set_volume(value)
    assert e.value.code == "tv_volume_invalid"


async def test_leiser_als_null_wird_null(configured):
    configured.volume = 3
    assert (await client.set_volume("-10"))["volume"] == 0


async def test_stumm(configured):
    assert (await client.set_mute(True))["muted"] is True
    assert (await client.set_mute(False))["muted"] is False


async def test_ein_aus(configured):
    off = await client.set_power(False)
    assert off["power"] == "standby" and off["volume"] is None
    assert (await client.set_power(True))["power"] == "on"


async def test_apps_und_starten(configured):
    apps = await client.apps()
    assert [a["name"] for a in apps] == ["Netflix", "Plex", "YouTube"]
    r = await client.start_app("plex")
    assert r == {"started": "Plex"}
    assert any(c[1] == "setActiveApp" and c[2][0]["uri"].endswith("SplashActivity") for c in configured.calls)


async def test_app_unbekannt(configured):
    with pytest.raises(client.TVError) as e:
        await client.start_app("Disney+")
    assert e.value.code == "tv_app_unknown"


async def test_nicht_eingerichtet(fake_tv):
    with pytest.raises(client.TVError) as e:
        await client.status()
    assert e.value.code == "tv_not_configured"


@pytest.mark.parametrize(("mode", "psk", "code"), [("unreachable", PSK, "tv_unreachable"),
                                                   ("needs_restart", PSK, "tv_needs_restart"),
                                                   ("ok", "falsch", "tv_auth_failed")])
async def test_fehler_klar_benannt_und_ohne_schluessel(configured, mode, psk, code):
    configured.mode = mode
    configured.psk = psk if psk != PSK else PSK
    if psk != PSK:
        configured.psk = "anders"
    with pytest.raises(client.TVError) as e:
        await client.status()
    assert e.value.code == code
    assert PSK not in str(e.value)


async def test_verbindung_testen(configured):
    assert await client.test() == {"ok": True, "model": "KD-60XF8305", "power": "on"}


async def test_eigene_grenze_aus_den_einstellungen(configured):
    from backend import settings_store
    settings_store.save(name="TV", address="192.168.178.186", psk=None, volume_limit=30, user="admin")
    configured.volume = 25
    with pytest.raises(client.TVError) as e:
        await client.set_volume("31")
    assert e.value.code == "tv_volume_limit"
    assert (await client.set_volume("30"))["volume"] == 30


async def test_404_im_fehlerfeld_heisst_neustart(configured, monkeypatch):
    """Der echte TV antwortete mit HTTP 200 und {"error": [404, "Not Found"]}, nicht nur mit HTTP 404."""
    from backend import client as c

    async def http200_mit_404(ip, service, method, params, version, psk):
        return 200, {"error": [404, "Not Found"]}
    monkeypatch.setattr(c, "_post", http200_mit_404)
    with pytest.raises(client.TVError) as e:
        await client.status()
    assert e.value.code == "tv_needs_restart"


async def test_umschalten_ignoriert_meldet_klar_statt_erfolg(configured):
    """Bleibt der TV auf dem alten Sender, kommt ein Fehler – kein vorgetäuschter Erfolg."""
    configured.ignore_switch = True
    with pytest.raises(client.TVError) as e:
        await client.set_channel("ZDF")
    assert e.value.code == "tv_switch_failed" and configured.playing["title"] == "SAT.1"
    assert sum(1 for c in configured.calls if c[1] == "setPlayContent") == 2      # einmal wiederholt, nicht öfter


async def test_umschalten_aus_einer_app_wiederholt_einmal(configured):
    """Gemessen 29.10.: aus einer App heraus wirkt erst der zweite Befehl."""
    configured.app_open = True
    s = await client.set_channel("ZDF")
    assert s["channel"] == {"number": 2, "name": "ZDF HD"}
    assert sum(1 for c in configured.calls if c[1] == "setPlayContent") == 2


async def test_umschalten_im_normalfall_nur_ein_befehl(configured):
    await client.set_channel("kabel eins")
    assert sum(1 for c in configured.calls if c[1] == "setPlayContent") == 1


async def test_umschalten_auf_aktuellen_sender_ist_erfolg(configured):
    s = await client.set_channel("SAT.1")
    assert s["channel"] == {"number": 6, "name": "SAT.1"}



# --- Über der Grenze: leiser geht immer (Befund 29.10.: Receiver meldet 62 bei Grenze 30) ----------------------

@pytest.mark.parametrize(("start", "value", "end"), [(62, "-1", 61), (62, "-20", 42), (62, "50", 50), (45, "30", 30),
                                                     (50, "30", 30), (35, "-5", 30), (31, "-1", 30)])
async def test_leiser_geht_auch_ueber_der_grenze(configured, start, value, end):
    from backend import settings_store
    settings_store.save(name="TV", address="192.168.178.186", psk=None, volume_limit=30, user="admin")
    configured.volume = start
    assert (await client.set_volume(value))["volume"] == end


@pytest.mark.parametrize(("start", "value"), [(62, "-21"), (62, "41"), (62, "30"), (62, "+1"), (62, "62")])
async def test_ueber_der_grenze_nur_leiser_und_nur_in_schritten(configured, start, value):
    """Leiser ja, aber höchstens 20 auf einmal; gleich laut oder lauter bleibt verboten."""
    from backend import settings_store
    settings_store.save(name="TV", address="192.168.178.186", psk=None, volume_limit=30, user="admin")
    configured.volume = start
    with pytest.raises(client.TVError) as e:
        await client.set_volume(value)
    assert e.value.code == "tv_volume_limit"
    assert configured.volume == start


async def test_ton_ueber_den_receiver_wird_gemeldet(configured):
    configured.output = "audioSystem"
    s = await client.status()
    assert s["output"] == "receiver"


async def test_ton_ueber_den_fernseher(configured):
    assert (await client.status())["output"] == "speaker"


async def test_unbekannte_ausgabe_bleibt_ehrlich(configured):
    configured.output = "headphone"
    s = await client.status()
    assert s["output"] == "other"


async def test_ausgabe_aus_den_toneinstellungen_mit_version_1_1(configured):
    configured.output = "audioSystem"
    await client.status()
    asked = [c for c in configured.calls if c[1] == "getSoundSettings"]
    assert asked and all(c[3] == "1.1" for c in asked)
    assert asked[0][2] == [{"target": "outputTerminal"}]


async def test_ohne_toneinstellungen_unbekannt_statt_fehler(configured):
    """Kennt der TV getSoundSettings nicht, bleibt der Status lesbar – Ausgabe unbekannt."""
    configured.output = None
    s = await client.status()
    assert s["power"] == "on" and s["volume"] == 14 and s["output"] == "other"
