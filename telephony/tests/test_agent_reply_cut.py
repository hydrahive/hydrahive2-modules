"""Till 25.10.: 3 von 4 Antworten kamen als „nicht verstanden“ an. Ursache war nicht Whisper, sondern eine abgeschnittene
Modellantwort (Längengrenze zu knapp): ``{"say": "Am Wochenende ist Alex nicht erreichbar, aber … Einen genaueren Ze``.
Die halbe Antwort wurde verworfen. Jetzt: genug Platz für die Antwort, und ein abgeschnittener Satz wird bis zum letzten
ganzen Satz gesprochen statt „nicht verstanden“.
"""
from __future__ import annotations

import logging


def test_grenze_fuer_die_antwortlaenge_reicht() -> None:
    from backend import assistant

    assert assistant.MAX_TOKENS >= 1500


def test_abgeschnittene_antwort_bis_zum_letzten_ganzen_satz() -> None:
    from backend.agent.reply import parse_reply

    r = parse_reply('{"say": "Am Wochenende ist Alex nicht erreichbar. Er ruft Sie am Montag zurück. Einen genaueren Ze')
    assert r.ok and r.say == "Am Wochenende ist Alex nicht erreichbar. Er ruft Sie am Montag zurück."
    assert r.notes == {} and r.end is False, "aus einer halben Antwort werden keine Notizen und kein Auflegen abgeleitet"


def test_abgeschnitten_mit_fragezeichen_und_escapes() -> None:
    from backend.agent.reply import parse_reply

    r = parse_reply('{"say": "Danke, ich habe \\"0610\\" notiert. Darf ich noch Ihren Namen erfahren? Und', )
    assert r.ok and r.say == 'Danke, ich habe "0610" notiert. Darf ich noch Ihren Namen erfahren?'


def test_abgeschnitten_ohne_ganzen_satz_bleibt_rueckfrage() -> None:
    from backend.agent.reply import FALLBACK_SAY, parse_reply

    for raw in ['{"say": "Ich habe', '{"say": "', '{"sa', "", "kein json"]:
        r = parse_reply(raw)
        assert not r.ok and r.say == FALLBACK_SAY, raw


def test_vollstaendige_antwort_unveraendert() -> None:
    from backend.agent.reply import parse_reply

    r = parse_reply('{"say": "Gern. Auf Wiederhören!", "notes": {"name": "Max Mustermann"}, "end": true}')
    assert r.ok and r.say == "Gern. Auf Wiederhören!" and r.notes == {"name": "Max Mustermann"} and r.end


def test_kaputte_antwort_wird_protokolliert_ohne_inhalt(caplog) -> None:
    """Beim echten Anruf stand nichts im Protokoll – deshalb sah es nach Whisper aus. Inhalt bleibt draußen (Anrufer)."""
    from backend.agent.reply import parse_reply

    with caplog.at_level(logging.WARNING):
        parse_reply('{"say": "Geheimer Anrufertext ohne Satzende')
        parse_reply('{"say": "Bitte Rückruf Musterstraße. Und ein hal')
    text = caplog.text
    assert text.count("telephony:") == 2 and "Geheim" not in text and "Musterstraße" not in text
