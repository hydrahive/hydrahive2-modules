# Plan Mailbox M3a – Freigabe je Projekt (lesen) und Lese-Werkzeuge für Agenten

Spec: `mailbox/SPEC.md` §7, §8 (freigegeben 21.10.2026). Till 23.10.: „mergen, danach dann weiter“. Version 0.6.0.

## Ziel

Der Besitzer eines Mailkontos gibt es für ein Projekt (oder für seinen eigenen Buddy ohne Projekt) **zum Lesen**
frei. Agenten in diesem Projekt können dann suchen, lesen und Anhänge in ihren Arbeitsordner holen – nur in
freigegebenen Konten, jede Aktion steht im Protokoll (ohne Mailinhalt).

## Entscheidungen

- Freigabe-Ziel: `project:<id>` oder `buddy` (nur der Besitzer selbst, ohne Projekt).
- Stufe in M3a nur `read`. Die Spalte `level` ist da; `draft`/`send` kommen mit M3b/M4.
- Ein Werkzeug sieht ein Konto nur, wenn (a) eine Freigabe für `ctx.project_id` besteht **und** der Nutzer des
  Laufs Mitglied des Projekts ist (System-Admin: immer), bzw. (b) ohne Projekt: Freigabe `buddy` und der Nutzer ist
  der Besitzer. Ohne passende Freigabe: Konto unsichtbar (nicht „verboten“).
- Mailinhalt ist fremder Text: Ausgabe zwischen `<<<MAIL-INHALT …>>>` und `<<<ENDE MAIL-INHALT>>>`.
- Keine Zugangsdaten, kein Passwort, kein Roh-Header in Werkzeug-Ausgaben.
- `sensitive_tools`: alle vier Werkzeuge `privat`. `default_agent_tools: true` (Master-Agenten bekommen die
  Werkzeuge; ohne Freigabe liefern sie nichts).
- Anhang: höchstens 25 MB, sicherer Dateiname, nie überschreiben, Ziel `<arbeitsordner>/mailbox-anhaenge/`.
- Ordner-Einschränkung und Vault-PIN je Konto: nicht in M3a.

## Dateien

- `migrations/004_m3_shares.sql` – `module_mailbox_shares`, `module_mailbox_audit`.
- `backend/shares.py` – Freigaben anlegen/entfernen/auflisten; erlaubte Konten für einen Werkzeuglauf.
- `backend/share_routes.py` – `GET/PUT/DELETE /accounts/{aid}/shares…` (nur Besitzer).
- `backend/agent_audit.py` – Protokoll ohne Inhalt.
- `backend/agent_tools.py` – die vier Werkzeuge.
- `frontend/AccountShares.tsx` + `api.ts` + `i18n.ts` – Freigaben im Kontodialog.
- Tests: `test_shares.py`, `test_agent_tools.py`, Frontend-Test der Freigabeliste.

## Reihenfolge (je Schritt Test zuerst)

1. Migration + `shares.py` (Besitz, Projektmitgliedschaft, Buddy, Entfernen bei Kontolöschung).
2. Routen (fremdes Konto = 404, ungültiges Projekt = 422, kein Mitglied = 404).
3. Werkzeuge + Protokoll (Sichtbarkeit, Markierung, Grenzen, Anhang-Pfad).
4. Oberfläche, Manifest 0.6.0, Handbuch (Core-PR).

## Akzeptanz

- [ ] Agent im freigegebenen Projekt findet und liest Mails des Kontos.
- [ ] Agent in einem anderen Projekt sieht das Konto nicht.
- [ ] Nicht-Mitglied des Projekts sieht nichts, auch mit Freigabe.
- [ ] Buddy ohne Projekt sieht nur `buddy`-Freigaben des eigenen Kontos.
- [ ] Ausgaben sind als Fremdinhalt markiert; keine Geheimnisse.
- [ ] Anhang landet im Arbeitsordner, nie außerhalb, nie überschrieben.
- [ ] Jede Werkzeug-Aktion steht im Protokoll, ohne Mailinhalt.

## Nicht in M3a

Entwürfe/Verschieben/Markieren durch Agenten (M3b), Senden mit Bestätigung (M4), gemeinsame Konten (Gruppe).
