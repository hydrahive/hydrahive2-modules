# Hydra-Labor – Bauplan Etappe L3 (Probe ansehen)

> Wunsch Till (30.10.): „Der Nutzer muss im Browser sehen können, was er gebaut hat.“ (SPEC.md: Probe-Installation.)
> Ziel: Im Labor läuft ein **Probe-HydraHive** aus dem Labor-Stand. Der Admin öffnet es über einen Knopf im Browser.
> Der Server und das Heimnetz bleiben weiter **zu** – vom Labor aus und von außen.

## Rahmen

- Die Sperre aus L1 gilt weiter: Das Labor erreicht den Server nicht. Der Weg geht nur **vom Server ins Labor**,
  auf genau einen Port, und nur für angemeldete Admins.
- Das Probe-HydraHive hat **eigene, leere Daten** und einen eigenen Admin. Es kennt keine Schlüssel, Zugänge oder
  Daten des echten Servers. LLM-Zugänge trägt der Admin dort selbst ein, wenn er sie braucht.

## Bausteine

1. **Probe bauen** (Auftrag im Hintergrund, Knopf „Probe bauen“):
   - im Labor als `labor`: `npm run build` im Kern-Frontend (Labor-Stand), Python-Umgebung ist schon da.
   - Datenordner `/work/.probe/data`, `/work/.probe/config`, Admin `admin` mit zufälligem Passwort, das die
     Labor-Seite einmal anzeigt („Anmelden in der Probe mit …“).
   - Module aus `/work/hydrahive2-modules`: der Admin wählt in der Probe selbst, welche er installiert (Probe hat die
     Modulverwaltung). Der Modul-Hub der Probe zeigt auf den Labor-Ordner, nicht auf GitHub.
   - Bauzeit und Platz **vorher messen** (Erwartung: Build 1–3 min, ~300 MB).
2. **Probe starten/stoppen**: Dienst im Labor (`systemd --user` oder einfacher Hintergrundprozess unter `labor`),
   Backend lauscht im Labor auf `0.0.0.0:8001`, liefert die gebaute Oberfläche mit aus (wie im Installer).
3. **Durchreiche** (der heikle Teil) – zwei Wege, Entscheidung durch Till:
   - **A) Eigener Port am Server** (Muster Radiostream-Hörerseite): nginx-Block auf z. B. `8443` mit dem
     TLS-Zertifikat des Servers, `proxy_pass` an `<Labor-IP>:8001`. Davor **Anmeldeprüfung des Haupt-HydraHive**
     (`auth_request` gegen einen Kern-Endpunkt „bin ich Admin?“). Die Probe läuft unverändert, weil sie unter `/`
     liegt. Port nur im Heimnetz/Tailscale offen, nicht ins Internet.
   - **B) Unterpfad im Haupt-HydraHive** (`/labor-probe/…`): kein zusätzlicher Port, aber die Probe-Oberfläche
     müsste unter einem Unterpfad laufen (Kern-Frontend nutzt fest `/api` und `/assets`) → Kern-Änderung nötig,
     Cookies/Speicher teilen sich die Adresse mit dem echten HydraHive (Verwechslungsgefahr bei der Anmeldung).
   - **Empfehlung A.** B ist aufwendiger und riskanter (gleiche Adresse wie das echte System).
4. **Sperre bleibt**: Die ACL erlaubt nur **eingehend** vom Server-Gateway auf Port 8001 ins Labor (neue Regel
   `ingress allow source=<Gateway> destination-port=8001`), alles andere ein- und ausgehend wie in L1.
   Die Netzprobe aus L1 prüft weiter, dass das Labor den Server NICHT erreicht.
5. **Labor-Seite**: Kasten „Probe“ mit Stand (aus / baut / läuft), Knöpfe „Probe bauen“, „Starten“/„Stoppen“,
   „Probe öffnen“ (neuer Tab), Zugangsdaten der Probe (einmal anzeigen, „neu erzeugen“).
6. **Zurücksetzen/Entfernen**: Probe-Daten liegen im Labor → gehen mit „Zurücksetzen“ zurück auf frisch; nginx-Block
   und Port werden bei „Labor entfernen“ mit entfernt (nur was im Zustand als angelegt steht).

## Sicherheit

- Durchreiche nur mit gültiger Anmeldung als **Admin** am echten HydraHive (sonst 401/403, Probe nie erreichbar).
- Kein Token/Cookie des echten HydraHive wird an die Probe weitergereicht (`proxy_set_header Authorization ""`,
  Cookie-Kopf entfernen bis auf den eigenen der Probe).
- nginx-Block aus Datei (wie Radiostream), `nginx -t` vor dem Laden, alte Fassung bei Fehler zurück.
- Probe-HydraHive: `HH_SECRET_KEY` eigen und zufällig, keine Umgebungsvariablen des Servers.
- Ausbruchsproben erweitert: Aus dem Labor bleibt der Server zu (auch der neue Port); von außen ohne Anmeldung zu.

## Tests

- Rot zuerst; incus und root-Befehle als Attrappe wie in L1/Radiostream.
- ACL: genau eine neue eingehende Regel, ausgehend unverändert; Netzprobe weiter grün.
- nginx-Block: Inhalt (Port, Ziel-IP, auth_request, Kopf-Entfernung), Rücknahme bei `nginx -t`-Fehler.
- Anmeldeprüfung: ohne Anmeldung, als Nutzer, als Admin.
- Mutanten, Gegenprobe, volle Reihe; **echt** auf hydratest: Probe bauen (Zeit/Platz messen), öffnen im Browser,
  dort anmelden, eine Änderung im Labor → „Probe bauen“ → Änderung sichtbar; E2E 4 Breiten.

## Offene Fragen an Till

1. Durchreiche **A (eigener Port)** oder **B (Unterpfad)**? Empfehlung A.
2. Welcher Port? Vorschlag **8443** (frei auf .2 und hydratest prüfen).
3. Plugins als drittes Ziel beim Einreichen (aus L2 verschoben) – in L3 mitnehmen?

## Entscheidungen (Till, 30.10.)

1. Durchreiche **A – eigener Port** am Server (nginx mit Anmeldeprüfung), kein Kern-Eingriff für die Probe selbst.
2. Port **8443** (gemessen frei auf .2 und hydratest am 30.10.). Nur Heimnetz/Tailscale, nicht ins Internet.
3. **Annahme** (nicht ausdrücklich beantwortet): Plugins als drittes Ziel beim Einreichen bleiben außerhalb von L3
   und kommen als eigene kleine Etappe danach.
