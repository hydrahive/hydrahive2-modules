# Module tragen ihren Bereich selbst ein (`nav.area`)

Etappe 2 der Startseite mit Bereichen (Kern: `docs/specs/startdesktop.md`, PR hydrahive2.0#618, Task 81a59975).

## Was

Jedes Modul mit einem Menüeintrag gibt in seinem `nav`-Eintrag (`frontend/index.tsx`) den Bereich an, in dem
es auf der Startseite und in der Bereichs-Leiste steht:

```ts
export const nav = [
  { path: "/studio", icon: "Clapperboard", labelKey: "studio", group: "working", area: "medien", ... },
]
```

Erlaubte Kennungen, festgelegt im Kern in `frontend/src/features/startdesk/areas.ts`:

| Kennung | Bereich |
|---|---|
| `medien` | Medienstudio |
| `schreiben` | Schreibbüro |
| `wissen` | Wissen & Recherche |
| `agenten` | Arbeiten mit Agenten |
| `kommunikation` | Kommunikation |
| `zuhause` | Zuhause & Privat |
| `freizeit` | Freizeit |
| `verwaltung` | Verwaltung (nur Admins) |

## Warum

- Bisher sortiert der Kern Module über eine feste Pfad-Tabelle ein.
- Ein neues Modul ohne Eintrag landet dort unter „Weitere“.
- Mit `area` entscheidet das Modul selbst, und der Kern muss für neue Module nicht geändert werden.
- Der Kern wertet `area` seit #618 aus. Es hat Vorrang vor der Tabelle, eine unbekannte Kennung fällt auf die
  Tabelle zurück.

## Zuordnung (wie in der Kern-Tabelle, von Till am 24.10.2026 freigegeben)

| Bereich | Module |
|---|---|
| medien | studio, atelier, videoeditor, tonstudio, musicplayer |
| schreiben | storyteller, notizbuch, scratchpad, diagramme, blueprint |
| wissen | deepresearch, archiver, legal (`/recht`), opentor |
| agenten | tickets |
| kommunikation | mailbox, telephony (`/voip`), voice |
| zuhause | haushaltsbuch, patientenakte (`/akte`), homeassistant, cryptoboard, mining, vitrine |
| freizeit | mediacenter, boardgames, minigames, vr |
| verwaltung | ai-security |

- Ohne `area`: `example` (wird nicht gezeigt) und `tasks` (hat keinen Menüeintrag).
- Die Kern-Tabelle bleibt unverändert als Rückfall für ältere Kern-Stände und Fremdmodule.

## Wie

- In `frontend/index.tsx` jedes Moduls im `nav`-Eintrag `area: "<kennung>"` ergänzen. Sonst ändert sich nichts.
- Jedes geänderte Modul bekommt einen Patch-Versionssprung (`x.y.z → x.y.z+1`).
  `scripts/check_version_bump.py origin/main` muss grün sein.
- Neuer Repo-Test `scripts/tests/test_nav_area.py`:
  - Jedes Modul mit `nav`-Pfad außer `example` hat genau eine gültige `area`.
  - Die Zuordnung entspricht der Tabelle oben, damit nichts versehentlich verrutscht.
  - Es gibt keine Kennung außerhalb der erlaubten Liste.

## Akzeptanzkriterien

- `python -m pytest scripts/tests` grün. Der neue Test ist auf `main` rot.
- `scripts/check_version_bump.py origin/main` und `scripts/check_test_safety.py` grün.
- Modul-Frontend-Tests gegen den Kern `main`: keine neue rote Datei gegenüber dem Ausgangsstand. Bekannt rot
  sind die zwei Studio-Seiten-Tests, siehe Task „Studio: 2 Seiten-Tests …“.
- hydratest nach dem Modul-Update: Startseite und Leiste zeigen dieselben Bereiche wie vorher. Kein Modul steht
  in „Weitere“, keine rohen Namen.

## Nicht enthalten

- Kern-Tabelle verkleinern (erst wenn alle Installationen neue Module haben).
- Neue oder umbenannte Bereiche.
