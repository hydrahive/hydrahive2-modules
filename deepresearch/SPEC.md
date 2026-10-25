# Deep Research – ausführlich statt abgeschnitten

Meldung von Till am 25.10.2026: Deep Research findet keine Ergebnisse mehr, selbst bei „was ist mirtazipin“. Man
sieht, wo er sucht, am Ende kommen aber keine Treffer. Wunsch: **Deep Research soll ausführlich schreiben, die
Grenzen also entsprechend hoch.**

## Befund (Hauptserver, nur gelesen)

- SearXNG liefert Treffer (Mirtazapin: 10–15 je Frage). Die Suche ist in Ordnung.
- Die Läufe vom 25.10. (Modell claude-opus-5-5) fanden 27/74/91 Seiten, davon 2/0/0 Quellen.
- Ursache: Die Auswertung je Seite (`extractor.py`) war auf **700 Token** begrenzt. Opus 5.5 schreibt bei
  Medizinfragen länger, die JSON-Antwort bricht mitten im Satz ab. `parse_json` gibt dann `{}` zurück, und die Seite
  wird **ohne Meldung** verworfen. Gegenprobe mit derselben Seite: 700 → verworfen, 2000 → vollständig, relevant.
- Weitere feste Grenzen: Planung 600, Suchbegriffe 400, laufende Zusammenfassung 2500, Bericht **4096** (bei
  „mind. 1200 Wörter“ zu knapp), Stopp-Frage 10.
- Opus 5.5 erlaubt bis 128.000 Token Antwortlänge (gemessen, 400.000 → 400 „max 128000“).

## Änderung

1. **Grenzen an einer Stelle** (`research/budgets.py`), großzügig:

   | Schritt | vorher | neu |
   |---|---:|---:|
   | Planung | 600 | 4.000 |
   | Suchbegriffe | 400 | 2.000 |
   | Auswertung je Seite | 700 | 8.000 |
   | laufende Zusammenfassung | 2.500 | 16.000 |
   | Bericht | 4.096 | 32.000 |
   | Stopp-Frage (nur YES/NO) | 10 | 50 |

   Bezahlt wird, was geschrieben wird, nicht die Grenze. Eine hohe Grenze kostet nichts extra, sie schneidet nur
   nicht mehr ab. 32.000 beim Bericht bleibt unter der 10-Minuten-Grenze des Anthropic-SDK für Antworten ohne
   Streaming (SDK: 3600 s × max_tokens / 128.000 ≤ 600 s → bis 21.333 ohne Streaming). Der Bericht geht deshalb
   **über Streaming** (`hydrahive.llm.client.stream`, Kern-Baustein, gibt es für alle Anbieter).
2. **Ausführlicher schreiben** (Prompts):
   - Auswertung je Seite: „gründlich“ statt „2–4 Sätze“. Alle relevanten Fakten, Zahlen, Dosierungen, Warnhinweise,
     Studien und Quellenangaben der Seite.
   - Laufende Zusammenfassung: nichts kürzen oder streichen, Bericht wächst.
   - Bericht: „mind. 2500 Wörter, so ausführlich wie das Material trägt“, eigene Abschnitte je Teilfrage, Tabellen,
     wo es hilft.
3. **Nichts mehr stillschweigend verwerfen**: Die Auswertung zählt *nicht auswertbar* (leere/kaputte Antwort) getrennt
   von *nicht relevant*.
   - Eine nicht auswertbare Antwort wird **einmal wiederholt**, mit dem Hinweis „NUR gültiges JSON“.
   - Bleibt sie kaputt, steht das in den Zahlen (`stats.unreadable`, `stats.irrelevant`, `stats.empty_pages`).
   - Ohne Quellen sagt der Bericht in einfachen Worten, warum, z. B. „74 Seiten gefunden, 70 davon konnten nicht
     ausgewertet werden“, statt nur „Keine verwertbaren Quellen gefunden“.
4. **Zeitbudget**: Die Läufe brauchen mit ausführlichem Schreiben länger. `max_time` geht von 300 s auf 900 s, die
   Runden bleiben bei höchstens 6.

Nicht enthalten: andere Suchquellen (Tavily), Modellwahl, Oberfläche (außer den neuen Zahlen im Bericht).

## Prüfung

- Rote Tests vorher, mit einem Test-Modell **ohne echte Aufrufe**:
  - Eine Antwort wird an der Grenze abgeschnitten (simuliert `max_tokens`) und ist mit den alten Grenzen kaputt.
  - Die Grenzen je Schritt werden wirklich übergeben.
  - Eine kaputte Antwort → 1 Wiederholung → Quelle zählt.
  - Zweimal kaputt → `unreadable`.
  - Der Bericht geht über `stream`.
  - Der Bericht ohne Quellen nennt die Zahlen.
- Mutanten, Gegenprobe gegen main, volle Modul-Tests.
- Echte Probe (Opus 5.5) nur nach Tills OK: eine Frage, Kosten vorher genannt.
