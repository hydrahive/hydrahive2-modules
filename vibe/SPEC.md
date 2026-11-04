# Vibe – beschreiben, ansehen, weitermachen

> Neues Modul `vibe`. Wunsch von Till (31.10.2026, kam „oft als Wunsch rein“): **„Vibe anklicken, Projekt auswählen,
> und los gehts.“**
> **Status: Entwurf, Design-Phase. Gebaut wird erst nach Tills Freigabe, Etappe für Etappe.**

## Problem

Vibe Coding heißt: Man beschreibt, was man will, sieht sofort das Ergebnis und korrigiert im Gespräch. Wer das heute in
HydraHive versucht, braucht die Werkstatt (Chat mit Projekt-Agent), muss das Ergebnis selbst starten und ansehen und
kann einen kaputten Zwischenstand nur mit Git-Kenntnissen zurückholen. Der Agent führt außerdem Befehle **auf dem Server**
aus (`tools/_launcher.py`, nur `DevLauncher`), wenn das Projekt nicht im Container läuft.

## Ziel

1. **Ein Klick:** „Vibe“ im Menü, ein Projekt wählen oder neu anlegen, Chat tippen. Keine Einrichtung, kein Terminal.
2. **Live-Vorschau:** Links Chat, rechts die laufende App. Nach jeder Antwort des Agenten lädt die Vorschau neu.
3. **Zeitmaschine:** Jeder Schritt ist eine Version. „Zurück zu vorhin“ ist ein Knopf, ohne Git-Wörter.
4. **Nichts kaputt machen:** Der Agent arbeitet nur in einem Container. Der Server bleibt unberührt.

## Was es schon gibt (nicht neu bauen)

| Baustein | Wo | Brauchbar für |
|---|---|---|
| Projekt-Ausführung im Container (K1): Feld `execution`, `ContainerLauncher`, Datei-Werkzeuge im Container, Allowlist der Werkzeuge | Kern `tools/_launcher_container.py`, `projects/execution.py`, `docs/specs/projekt-container-ausfuehrung.md` | Befehle und Dateien des Agenten im Container |
| Verwaltete Agenten (`managed_by`): Werkzeuge, Prompt und Projekt sind für den Nutzer gesperrt, nur das Modell darf er wählen | Kern `agents/_managed.py` | fester Vibe-Agent |
| Container anlegen, Netz abschotten, Schnappschüsse, Fortschritt | Modul `hydralabor`: `container.py`, `incus.py`, `network.py`, `provision.py`, `jobs.py` | Muster für den Container-Bau |
| **Probe im Browser** auf eigenem Ursprung (Port 8443, nginx `auth_request`, Ticket-Anmeldung, CSP) | `hydralabor/backend/probe_site.py`, `probe_auth.py`, `probe_net.py` | Muster für die Vorschau |
| „Zum Chat“ öffnet Projekt-Cockpit mit dem richtigen Agenten | `hydralabor/backend/lab_chat.py` | Chat öffnen |

Die Muster aus `hydralabor` werden **nicht** importiert: Ob ein Modul ein anderes importieren darf, ist nicht geprüft.
Entweder die Dateien werden kopiert und angepasst, oder gemeinsamer Code wandert in den Kern (Entscheidung in V1).

## Rahmen und Entscheidungen

- **Eigene Vibe-Projekte.** Vibe legt für jede App ein eigenes Projekt an (Name frei wählbar). „Projekt auswählen“ zeigt
  diese Vibe-Projekte und „Neues Projekt“. **Bestehende normale Projekte fasst Vibe nicht an.** Grund: K1 stellt ein
  Projekt auf `execution=container` um. Danach hätten seine Agenten nur noch die Allowlist und arbeiten unter `/work`,
  nicht mehr im bisherigen Arbeitsordner. Das wäre für ein laufendes Projekt eine stille Verhaltensänderung.
- **Ein Container je Vibe-Projekt**, Name `hh-vibe-<projekt>` (K1: `^[a-z][a-z0-9-]{1,62}$`). Grenzen als Vorschlag
  2 CPU / 2 GB RAM / 10 GB (Hydra-Labor misst mit 2 CPU / 4 GB: `npm run build` 15 s). **Vor dem Bau messen.**
- **Ruhender Container:** Nach 30 Minuten ohne Nutzung wird er gestoppt, beim Öffnen automatisch gestartet. Startzeit
  ist nicht gemessen.
- **Netz:** Internet offen (für `npm install`/`pip`), Heimnetz, Server und Router zu (wie Labor).
- **Vorschau auf eigenem Ursprung, nie im Ursprung von HydraHive.** Der Code im Container ist vom Agenten gerade erst
  geschrieben. Läuft er im selben Ursprung wie HydraHive, kann er den Login-Token aus dem `sessionStorage` lesen. Das
  Labor löst das über einen eigenen Port; dieselbe Regel gilt hier (`probe_site.py`: „:8443 ist ein anderer Ursprung“).
  Zusätzlich `<iframe sandbox>` ohne `allow-same-origin` und die CSP `connect-src 'self'`.
- **Zugriff:** Fähigkeit `module.vibe`, Standard `admin_only` (wie `hydralabor`), Admin gibt frei. Container verbrauchen
  Platz und Speicher.
- **Kein Mac:** Ohne `incus` (z. B. Mac ohne Colima) ist Vibe nicht verfügbar. Die Seite sagt das klar (wie K1).
- **Zeitmaschine über Git im Container, nicht über incus-Schnappschüsse.** Auf Tills Hauptserver liegt der incus-Pool
  als `dir` (Task `4d03dde2`, Befund 14.10., hier nicht erneut geprüft). Ein Schnappschuss ist dort eine volle Kopie.
  Ein Git-Commit nach jeder Agenten-Antwort ist klein und schnell. Ein incus-Schnappschuss „frisch“ nur für
  „ganz von vorn“.

## Aufbau

```
 Vibe-Seite (Modul, Frontend)
 ┌───────────────────────────┬──────────────────────────────┐
 │ Chat mit Vibe-Agent       │ Vorschau (iframe, eigener    │
 │ Zeitleiste: Versionen     │ Ursprung) + Konsolenfehler   │
 └───────────────────────────┴──────────────────────────────┘
        │ Befehle/Dateien                 ▲ Durchreiche mit Anmeldung
        ▼                                 │
 Container hh-vibe-<projekt>: /work (Git), Entwicklungs-Server auf Port 5173/8000
```

## Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| **V1 Grundgerüst** | Modul, Projekt anlegen (Container, Agent, Projekt), Seite mit Chat links und Vorschau rechts, Zeitmaschine (Git-Commit je Antwort, „Zurück“), Container ruht/startet von selbst | „Vibe anklicken, Projekt, los“ funktioniert mit einer leeren Webseite |
| **V2 Vorlagen + Fehler** | Vorlagen (leere Webseite, Vite + React, Flask-Seite, Spiel mit Canvas). Knopf „Fehler an den Agenten“ schickt Konsolenfehler der Vorschau in den Chat | wenig Tippen bis zur ersten lauffähigen App |
| **V3 Veröffentlichen** | Export als ZIP, optional statische Seite im Heimnetz/Tailscale | App verlässt den Container |
| **V4 Teilen** | Projekt für andere Nutzer freigeben (nur lesen oder mitbauen) | gemeinsames Bauen |

V1 allein ist ein vorzeigbares Produkt. V2 bis V4 nur nach Tills Entscheidung.

## Vibe-Agent (fest eingerichtet, `managed_by: "vibe"`)

- Systemprompt: kurze Schritte, nach jeder Änderung die Vorschau prüfen, einfache Sprache, auf Wunsch nachfragen statt
  raten, keine Secrets in den Code schreiben.
- Werkzeuge: die K1-Allowlist (`shell_exec`, `file_*`, `todo_write`, `load_skill`, `web_search`, `fetch_url` u. a.). Kein
  Mail, Discord, `ask_agent`, Browser mit lokalen Dateien.
- Modell: wählt der Nutzer aus seinen Anbietern. Vibe bringt keinen eigenen Schlüssel mit.

## Nicht enthalten

Eigene KI-Anbindung im Modul (nutzt die Anbieter des Servers), Hosting im Internet, Datenbank-Dienste außerhalb des
Containers, Zugriff auf Dateien des Servers, Vorlagen über V2 hinaus.

## Tests (Vorschlag, TDD)

1. **Isolation:** Befehle landen nur im Container (Attrappe für `incus`), keine Umgebungsvariablen des Servers.
2. **Fremdprojekt:** Vibe ändert `execution` nie bei einem Projekt, das es nicht selbst angelegt hat (Gegenprobe).
3. **Vorschau:** Antwort ohne gültige Anmeldung = 401. Anfragen aus der Vorschau erreichen den Server nicht (CSP).
4. **Zeitmaschine:** Nach „Zurück“ entspricht `/work` exakt der gewählten Version. Spätere Versionen bleiben erreichbar.
5. **Ruhezustand:** Nach der Leerlaufzeit ist der Container aus. Öffnen startet ihn, Vorschau kommt wieder.
6. **Ohne incus:** klare Meldung, kein halb angelegtes Projekt.

## Akzeptanzkriterien (V1)

- Ein Nutzer ohne Git- und Terminal-Kenntnisse legt in unter 2 Minuten ein Projekt an und sieht sein erstes Ergebnis.
- „Zurück“ holt jede frühere Version zurück, auch nach einem kaputten Schritt.
- Der Server ist vom Container aus nicht erreichbar (wie beim Labor geprüft).
- Auf hydratest echt abgenommen, mit echtem Agenten-Lauf.

## Offene Fragen an Till

1. **Eigene Vibe-Projekte statt bestehende Projekte umzustellen** (siehe Rahmen). OK so?
2. **Wer darf Vibe nutzen?** Vorschlag: zuerst nur Admins, später freigeben. Oder gleich für die Familie?
3. **Grenzen je Container:** 2 CPU / 2 GB / 10 GB als Start, oder lieber großzügiger?
