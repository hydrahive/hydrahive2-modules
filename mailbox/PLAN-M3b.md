# Plan Mailbox M3b – Stufe „Entwurf“ für Agenten (0.7.0)

Spec: `mailbox/SPEC.md` §7, §8. Till 23.10.: „M3b“.

## Ziel

Mit Freigabe-Stufe **Entwurf** dürfen Agenten im Projekt zusätzlich Entwürfe anlegen und ändern, Mails verschieben
und markieren. Senden und Löschen können Agenten nie. Den Entwurf prüft und sendet der Mensch selbst im Webmail.

## Entscheidungen

- Stufe je Freigabe: `read` | `draft` (umstellbar im Kontodialog). `send` folgt mit M4.
- Entwürfe eines Agenten gehören dem **Kontobesitzer** und erscheinen in seinem Webmail unter „Entwürfe“ mit
  Kennzeichen „Agent“.
- Ein Agent ändert **nur** Entwürfe, die in **diesem** Projekt von einem Agenten angelegt wurden
  (`module_mailbox_agent_made`) – nie die des Menschen, nie die eines anderen Projekts.
- Antworten/Weiterleiten über `mode` + `ref_message`: Empfänger, Betreff und Zitat kommen aus dem Original
  (gleiche Logik wie das Webmail, `reply.prefill`).
- Verschieben/Markieren laufen über denselben Weg wie das Webmail (`action_routes._run_account`):
  UID-Bestätigung, nie pauschales EXPUNGE, Archiv bleibt.
- Protokoll je Aufruf, ohne Inhalt.

## Mitgefundener Fehler

Das Schreibfenster legt das Zitat schon in den Text (`compose/prefill`); `reply.reply`/`reply.forward` hängten es
beim Senden **noch einmal** an → Original doppelt zitiert. Jetzt: nur anhängen, wenn die Kopfzeile des Zitats nicht
schon im Text steht (`reply._with_original`). Test `test_reply_quote_once.py`.

## Dateien

- `migrations/005_m3b_agent_made.sql`, `backend/agent_drafts.py`
- `backend/agent_tools_write.py` (mailbox_draft, mailbox_flag, mailbox_move), `backend/shares.py` (Stufen)
- `backend/reply.py` (Zitat einmal), `backend/compose_routes.py` (`by_agent` an Entwürfen)
- `frontend/AccountShares.tsx`, `frontend/DraftList.tsx`, `api.ts`, `i18n.ts`
- Tests: `test_agent_tools_draft.py`, `test_reply_quote_once.py`, `SharesView.test.tsx`

## Akzeptanz

- [x] Stufe „lesen“ darf nichts ändern; „Entwurf“ darf entwerfen, verschieben, markieren.
- [x] Agenten-Entwurf erscheint beim Besitzer mit Kennzeichen; Mensch-Entwürfe sind für Agenten tabu.
- [x] Löschen und Senden gibt es für Agenten nicht.
- [x] Antwort zitiert das Original genau einmal (Webmail und Agent).

## Nicht in M3b → M3c

Gemeinsame Konten (Gruppe): Besitz `group:<id>`, Verwaltung mit Recht `mailbox.manage_shared`, Sichtbarkeit für
Gruppenmitglieder in Webmail, Abgleich und Freigaben. Eigene Etappe, weil sie Besitzprüfungen in allen Routen ändert.
