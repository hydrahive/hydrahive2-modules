"""Sony-Client gegen den nachgebauten Fernseher (Werte wie am echten Gerät gemessen)."""
from __future__ import annotations

import pytest
from backend import client
from conftest import CHANNELS, PSK


async def test_status_liest_alles(configured):
    s = await client.status()
    assert s == {"power": "on", "channel": {"number": 6, "name": "SAT.1"}, "program": "Sendung SAT.1",
                 "volume": 14, "muted": False, "model": "KD-60XF8305"}


async def test_status_im_standby_ohne_sender(configured):
    configured.power = "standby"
    s = await client.status()
    assert s["power"] == "standby" and s["channel"] is None and s["program"] == ""


async def test_schluessel_geht_nur_in_die_kopfzeile(configured):
    await client.status()
    sent = [c for c in configured.calls if c[1] != "getInterfaceInformation"]
    assert sent and all(c[4].get("X-Auth-PSK") == PSK for c in sent)
    assert all(PSK not in repr(c[2]) for c in configured.calls)


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


@pytest.mark.parametrize("value", ["61", "100", "+50", "-21", "+21"])
async def test_lautstaerke_grenzen(configured, value):
    configured.volume = 40
    with pytest.raises(client.TVError) as e:
        await client.set_volume(value)
    assert e.value.code == "tv_volume_limit"
    assert configured.volume == 40


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
    assert (await client.set_power(False))["power"] == "standby"
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
