# Zieldokument: Wiki und PDF-Handbuch automatisch aus den Repos

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ja bitte mache das so“ – Wiki-Bau automatisch, PDF gleich mit,
> im Wiki bzw. als Release-Anhang verlinkt). Phase 5 von `ziele/hilfe-aktuell.md`.
> **Anlass:** Ein Nutzer fragte nach dem Wiki als PDF. Das Wiki wird heute von Hand auf dem Hauptserver gebaut
> (`_work/wiki/tools/sync_wiki.sh`, Stand 22.11.2026) und mischt Hilfe-Artikel mit Discord-Texten.

## 1. Zielbild
1. Das Wiki (`github.com/hydrahive/hydrahive2.0/wiki`) entsteht **nur** aus Dateien in den Repos:
   Kern-Hilfe `frontend/src/i18n/help/de/<topic>.md`, Modul-Hilfe `hydrahive2-modules/<modul>/frontend/help/de/<id>.md`,
   und wenige feste Rahmentexte (Startseite, „Was ist HydraHive?“) im Kern-Repo. Keine Discord-Quelle, kein Server-Pfad.
2. Ein **PDF-Handbuch** wird bei jedem Wiki-Bau mitgebaut: Deckblatt mit Stand, Inhaltsverzeichnis nach Bereichen,
   alle Seiten, Wiki-Links als Sprünge im PDF, Lesezeichen, Seitenzahlen.
3. **Automatisch** per GitHub Action: bei Push auf `main` (Kern: Hilfe-Ordner oder Wiki-Werkzeug geändert), täglich
   einmal (fängt Modul-Änderungen ab) und von Hand startbar. Niemand muss auf einem Server etwas ausführen.
4. Das PDF liegt **an einer festen Adresse** und ist auf der Wiki-Startseite verlinkt:
   Release `handbuch` im Kern-Repo, Anhang `HydraHive-Handbuch.pdf` (wird bei jedem Bau ersetzt).

## 2. Regeln
- Fehlt für eine Seite ein Artikel, fehlt die Seite (nicht aus alten Quellen auffüllen). Lücken listet der Bau als Hinweis.
- Datenschutz-Prüfung wie bisher (`check_public`: Hostnamen, interne Pfade, Personennamen, Tokens) – Treffer brechen
  den Bau ab, nichts wird veröffentlicht.
- Kein neuer Schlüssel nötig, wenn das Kern-Repo sein eigenes Wiki mit `GITHUB_TOKEN` (contents: write) beschreiben
  darf. Geht das nicht, Bau trotzdem fertig stellen und Blocker nennen (Till legt dann ein Token an).
- PDF-Bau ohne externe Dienste außer der GitHub-API (Markdown → HTML wie im Wiki) und Chromium im Runner.
- Wiki-Werkzeug liegt im Kern-Repo (`scripts/wiki/`), Tests in `core/tests/`.

## 3. Nicht-Ziele
- Englisches Wiki (erst Deutsch, wie in `hilfe-aktuell.md`).
- Inhalte der 5 fehlenden Kern-Artikel (Admin-Cockpit, Archiv & Sicherung, Discord-Serververwaltung, Vault, Websuche) –
  die schreibt Phase 3. Bis dahin fehlen diese Seiten im Wiki.

## 4. Abnahme
| # | Prüfung |
|---|---|
| WK1 | `scripts/wiki/build.py` baut aus einem Kern- und einem Modul-Checkout das Wiki (Markdown) – Test mit Beispiel-Repos: Kern- und Modul-Artikel erscheinen, Seitenleiste nach Bereichen, keine Discord-Quelle im Code |
| WK2 | Datenschutz-Prüfung bricht bei Treffer ab (Test mit eingeschmuggeltem Hostnamen/Token; Gegenprobe) |
| WK3 | Fehlende Artikel: Seite fehlt, Bau läuft, Lücke steht im Protokoll (Test) |
| WK4 | PDF: Deckblatt + Inhalt + alle Seiten, Wiki-Links als interne Sprünge, keine `[[…]]`-Reste (Test auf HTML-Ebene; PDF-Prüfung im Workflow mit pdfinfo/pdftotext) |
| WK5 | Workflow `wiki.yml`: Push auf main (Hilfe/Werkzeug), täglich, von Hand; schreibt Wiki und ersetzt den Release-Anhang; Wiki-Startseite verlinkt das PDF |
| WK6 | Erster echter Lauf auf GitHub: Wiki aktualisiert, PDF unter der festen Adresse abrufbar, Seitenzahl/Inhalt stichprobenartig geprüft |
