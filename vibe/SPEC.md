# Vibe – beschreiben, ansehen, weitermachen

> Neues Modul `vibe`. Wunsch von Till (31.10.2026, kam „oft als Wunsch rein“): **„Vibe anklicken, Projekt auswählen,
> und los gehts.“**
> **Status: Entwurf, Design-Phase. Gebaut wird erst nach Tills Freigabe, Etappe für Etappe.**
> Till (4.11.): „Mach das, was am sinnvollsten ist, mit Vibe Coding kenne ich mich nicht aus.“ Die Entscheidungen unten
> sind darum Vorschläge des Entwicklers, mit Begründung. Till kann jede umwerfen.

## Für wen

**Einsteiger ohne Programmierkenntnisse** (Familie, Discord-Gäste). Wer programmieren kann und Terminal, Git und Tests
sehen will, hat die Werkstatt. Ein „Expertenmodus“ ist bewusst nicht Teil von Vibe: Das wäre ein zweites Produkt.

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
5. **Nachsteuern ohne Angst:** Jede Version zeigt in einfachen Worten, was sich geändert hat, und lässt sich einzeln
   zurücknehmen.
6. **Fehler beheben sich selbst:** Stürzt die App ab, bekommt der Agent die Fehlermeldung und versucht es selbst
   (höchstens 3-mal, mit Kostengrenze).
7. **Der Agent vergisst die Regeln nicht:** Eine Projektregeln-Datei `VIBE.md` hält fest, was der Nutzer will.

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
  diese Vibe-Projekte und „Neues Projekt“. **Bestehende normale Projekte fasst Vibe nicht an.** Der normale
  HydraHive-Projektworkspace des neuen Vibe-Projekts wird in den Container als `/work` eingehängt. Host-Dateimanager,
  Samba, Projektwerkzeuge und Container-Agent sehen dadurch denselben Datenbestand; es gibt keine zweite versteckte
  Kopie nur im Container.
- **Ein Container je Vibe-Projekt**, Name `hh-vibe-<projekt>` (K1: `^[a-z][a-z0-9-]{1,62}$`). Grenzen als Vorschlag
  2 CPU / 2 GB RAM / 10 GB (Hydra-Labor misst mit 2 CPU / 4 GB: `npm run build` 15 s). **Vor dem Bau messen.**
- **Ruhender Container:** Nach 30 Minuten ohne Nutzung wird er gestoppt, beim Öffnen automatisch gestartet. Startzeit
  ist nicht gemessen.
- **Netz:** Internet offen (für `npm install`/`pip`), Heimnetz, Server und Router zu (wie Labor).
- **Vorschau auf eigenem Ursprung, nie im Ursprung von HydraHive.** Der Code im Container ist vom Agenten gerade erst
  geschrieben. Läuft er im selben Ursprung wie HydraHive, kann er den Login-Token aus dem `sessionStorage` lesen. Das
  Labor löst das über einen eigenen Port (`probe_site.py`: „:8443 ist ein anderer Ursprung“).
  - **Wichtiger Unterschied zum Labor:** Die Probe des Labors sendet `X-Frame-Options: DENY` und lässt sich **nicht**
    einbetten. Die Vibe-Vorschau muss aber **neben dem Chat** erscheinen. Darum: kein `X-Frame-Options`, stattdessen
    `Content-Security-Policy: frame-ancestors <Adresse von HydraHive>` (nur HydraHive darf einbetten) und im Rahmen
    `<iframe sandbox="allow-scripts allow-forms">` **ohne** `allow-same-origin`. Das iframe-Dokument bekommt so einen
    „undurchsichtigen“ Ursprung und kommt nicht an den Speicher von HydraHive.
  - **Offen, vor V1 messen:** Der Cookie der Durchreiche (`hh_labor_probe`) gilt laut Labor-Kommentar auch für das
    echte HydraHive, weil Cookies nicht nach Port trennen. Ob die Vorschau stattdessen mit einem Ticket in der Adresse
    (kurzlebig, einmalig) sauberer geht, ist nicht geprüft.
- **Zugriff:** Fähigkeit `module.vibe`, Standard `admin_only` (wie `hydralabor`), Admin gibt frei. Container verbrauchen
  Platz und Speicher.
- **Kein Mac:** Ohne `incus` (z. B. Mac ohne Colima) ist Vibe nicht verfügbar. Die Seite sagt das klar (wie K1).
- **Zeitmaschine über Git im Container, nicht über incus-Schnappschüsse.** Auf Tills Hauptserver liegt der incus-Pool
  als `dir` (Task `4d03dde2`, Befund 14.10., hier nicht erneut geprüft). Ein Schnappschuss ist dort eine volle Kopie.
  Ein Git-Commit nach jeder Agenten-Antwort ist klein und schnell. Ein incus-Schnappschuss „frisch“ nur für
  „ganz von vorn“.
- **Version = Git-Commit nach jeder Antwort.** Der Kurztext der Version ist die erste Zeile der Agenten-Antwort
  (höchstens 100 Zeichen, kein zusätzlicher KI-Aufruf). Dazu zeigt die Zeitleiste die Dateiliste aus `git diff --stat`
  („3 Dateien geändert“) und auf Klick die Änderung selbst, **ohne Git-Wörter** (Vorher/Nachher statt `diff`).
- **„Zurück zu hier“:** stellt den Stand der gewählten Version als **neue** Version wieder her
  (`git checkout <version> -- .`, dann Commit „Zurück zu …“). Es geht nie etwas verloren, auch nicht die Versionen
  dazwischen.
- **„Nur diese Änderung zurück“:** `git revert` der einen Version. Kommt es zu einem Konflikt mit späteren Änderungen,
  wird abgebrochen und es steht da: „Diese Änderung hängt mit späteren zusammen. Geh lieber zurück zu hier.“ Der
  Ablauf ist **nicht gebaut oder getestet**.

## Aufbau

```
 Vibe-Seite (Modul, Frontend)
 ┌───────────────────────────┬──────────────────────────────┐
 │ Chat mit Vibe-Agent       │ Vorschau (iframe, eigener    │
 │ Zeitleiste: Versionen     │ Ursprung) + Konsolenfehler   │
 └───────────────────────────┴──────────────────────────────┘
        │ Befehle/Dateien                 ▲ Durchreiche mit Anmeldung
        ▼                                 │
 HydraHive-Projektworkspace ↔ Container hh-vibe-<projekt>:/work (Git), Entwicklungs-Server auf Port 5173/8000
```

## Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| **V1 Kern** | Modul, Projekt anlegen (Container, Agent, Projekt), Seite mit Chat links und Vorschau rechts, Zeitleiste mit Änderungsansicht und Zurück, Fehler beheben sich selbst (3 Versuche), `VIBE.md`, Container ruht/startet von selbst | „Vibe anklicken, Projekt, los“ funktioniert mit einer leeren Webseite, Fehler und Zurück inklusive |
| **V2 Vorlagen + Veröffentlichen** | Vorlagen (leere Webseite, Vite + React, Flask-Seite, Spiel mit Canvas). „Veröffentlichen“: ZIP-Export und statische Seite im Heimnetz/Tailscale | wenig Tippen bis zur ersten App, App verlässt den Container |
| **V3 Teilen** | Projekt für andere Nutzer freigeben (nur ansehen oder mitbauen) | gemeinsames Bauen |

Fehler automatisch beheben ist bewusst in **V1**, nicht später: Es macht den Unterschied zwischen „spielt mit“ und „macht
es richtig“. V1 allein ist ein vorzeigbares Produkt. V2 und V3 nur nach Tills Entscheidung.

## Fehler beheben sich selbst (V1)

Quellen für Fehler, in dieser Reihenfolge der Einfachheit:
1. **Dev-Server und Build** im Container: Das Modul liest das Protokoll des Entwicklungs-Servers (Syntaxfehler,
   fehlende Pakete, Build-Fehler).
2. **Fehler im Browser** (Laufzeitfehler in der Vorschau): ein kleines Meldeskript in der ausgelieferten Seite schickt
   Fehler per `postMessage` an die Vibe-Seite. Ob die Durchreiche das Skript selbst einfügen kann oder die Vorlage es
   enthalten muss (der Agent könnte es löschen), ist **nicht geprüft**.

Ablauf: Fehler erkannt → Modul startet einen Agenten-Lauf in derselben Sitzung mit „Die App meldet diesen Fehler: …
Behebe ihn.“ Das Modul kann Agenten-Läufe selbst anstoßen: Das Storyteller-Modul macht es schon so
(`storyteller/backend/team_job_run.py`: `runner.run` bis zum Ende iterieren, Kostengrenze zwischen zwei Runden).
- **Höchstens 3 Versuche je Fehler.** Danach steht im Chat: „Ich komme nicht weiter. Beschreib mir, was du siehst.“
  Verhindert Endlosschleifen und Kosten.
- **Gleicher Fehler zweimal** hintereinander zählt als gescheitert, auch vor dem dritten Versuch.
- **Kostengrenze je Lauf** wie beim Storyteller. Wert vor dem Bau festlegen.
- Ausschaltbar mit einem Schalter in der Seite („Fehler selbst beheben“, Standard an).

## Projektregeln `VIBE.md` (V1)

Datei `/work/VIBE.md` im Projekt: Was soll die App sein, welche Technik, welcher Stil, was ist tabu („keine Bibliothek
X“, „Farben bleiben dunkelblau“). Der Agent legt sie in der ersten Antwort an, der Nutzer kann sie in der Seite ansehen
und ändern. Wirkung gegen das Vergessen bei langen Sitzungen: Der Vibe-Prompt verlangt, sie **vor jeder Änderung zu
lesen** und danach bei neuen Entscheidungen zu ergänzen. Die selbst ausgelösten Fehler-Läufe stellen den Inhalt der
Datei der Meldung voran. Ob der Kern den Inhalt automatisch in den Systemprompt legen kann (Hook an `project_layout_hint`),
ist **nicht geprüft**; der Weg über den Prompt reicht für V1.

## Vibe-Agent (fest eingerichtet, `managed_by: "vibe"`)

- Systemprompt: kurze Schritte, nach jeder Änderung die Vorschau prüfen, einfache Sprache, auf Wunsch nachfragen statt
  raten, keine Secrets in den Code schreiben, `VIBE.md` vor jeder Änderung lesen, jede Antwort mit **einer** kurzen
  Zeile beginnen, was geändert wurde (wird zum Text der Version).
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
   `/work` ist derselbe Datenbestand wie der normale HydraHive-Projektworkspace.
5. **Ruhezustand:** Nach der Leerlaufzeit ist der Container aus. Öffnen startet ihn, Vorschau kommt wieder.
6. **Ohne incus:** klare Meldung, kein halb angelegtes Projekt.
7. **Einbetten:** Die Vorschau lässt sich nur von der Adresse von HydraHive einbetten (`frame-ancestors`), von keiner
   anderen. Das iframe hat kein `allow-same-origin`.
8. **Fehler-Schleife:** Ein Fehler, der sich nicht beheben lässt, endet nach genau 3 Versuchen mit Hinweis. Gleicher
   Fehler zweimal in Folge bricht früher ab. Ausgeschaltet = kein Lauf.
9. **Zurück:** „Zurück zu hier“ verliert keine Version. „Nur diese Änderung zurück“ bricht bei Konflikt sauber ab und
   lässt `/work` unverändert.

## Akzeptanzkriterien (V1)

- Ein Nutzer ohne Git- und Terminal-Kenntnisse legt in unter 2 Minuten ein Projekt an und sieht sein erstes Ergebnis.
- Alle Quelldaten liegen im normalen HydraHive-Projektworkspace und sind dort über Dateimanager/Samba erreichbar; der
  Container sieht exakt diesen Workspace als `/work`.
- Bestehende Vibe-0.1.0-Projekte werden beim ersten Öffnen erst nach Kopie und Vergleich umgestellt; bei Fehler bleibt
  das ursprüngliche Container-`/work` erhalten.
- „Zurück“ holt jede frühere Version zurück, auch nach einem kaputten Schritt.
- Der Server ist vom Container aus nicht erreichbar (wie beim Labor geprüft).
- Ein absichtlich eingebauter Fehler wird vom Agenten selbst behoben, ohne dass der Nutzer etwas tut, und ein
  unlösbarer Fehler endet nach 3 Versuchen mit einem verständlichen Hinweis.
- Jede Version zeigt in einfachen Worten, was sich geändert hat.
- Die Vorschau lässt sich nicht von fremden Seiten einbetten.
- Auf hydratest echt abgenommen, mit echtem Agenten-Lauf.

## Entscheidungen des Entwicklers (Till 4.11.: „mach, was am sinnvollsten ist“) – Till kann widersprechen

1. **Eigene Vibe-Projekte** statt bestehende umzustellen: ja (Begründung im Rahmen oben).
2. **Wer darf Vibe nutzen:** zuerst nur Admins (Standard `admin_only`), Freigabe für die Familie, sobald V1 auf hydratest
   und danach auf dem Hauptserver abgenommen ist. Begründung: Container verbrauchen Platz und Speicher.
3. **Container-Grenzen:** 2 CPU / 2 GB / 10 GB als Start, **nach der ersten Messung auf hydratest anpassen**.
4. **Zielgruppe:** Einsteiger. Experten nutzen die Werkstatt.

## Noch offen (braucht Messung oder Till)

- Startzeit eines ruhenden Containers; Platz je Projekt; Wert der Kostengrenze je Fehler-Lauf.
- Cookie oder Ticket für die Vorschau-Anmeldung (siehe Vorschau).
- Meldeskript für Browser-Fehler: von der Durchreiche eingefügt oder in der Vorlage?
- Ob ein Modul ein anderes importieren darf; sonst Code kopieren oder gemeinsamen Teil in den Kern verlegen.
