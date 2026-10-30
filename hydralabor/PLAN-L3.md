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

## Nachtrag: Anmeldung an der Durchreiche (30.10., nach Freigabe gelesen)

- Das Login des echten HydraHive liegt im Browser im `sessionStorage` und wird bei einer Navigation **nicht**
  mitgeschickt. Ein Link auf `:8443` hat also keine Anmeldung.
- Muster im Kern: **AgentLink-Dashboard** (`api/routes/_agentlink_dashboard.py`): eigener, kurzlebiger, signierter
  Cookie, nur für Admins ausgestellt, nginx prüft per `auth_request` (Signatur, Ablauf, Nutzer existiert noch und ist
  Admin). Kein Login-Token, öffnet keine API.
- Für L3 genauso, aber **im Modul** (keine Kern-Änderung):
  1. `POST /api/modules/hydralabor/probe/open` (nur Admin) → einmaliges Ticket (zufällig, 60 s gültig, einmal
     benutzbar) und die Adresse `https://<host>:8443/__labor_login?t=<ticket>`.
  2. nginx auf 8443 leitet `/__labor_login` an das Modul (über die interne Adresse `127.0.0.1:8001`); das Modul löst
     das Ticket ein und setzt ein Cookie `hh_labor_probe` (HttpOnly, Secure, SameSite=Strict, Pfad `/`, 8 h,
     signiert mit zweckgebundenem Schlüssel aus `HH_SECRET_KEY`), dann Weiterleitung auf `/`.
  3. Jede andere Anfrage auf 8443: `auth_request` an `/api/modules/hydralabor/probe/auth` (Cookie prüfen wie beim
     AgentLink-Dashboard) → 204 oder 401. Erst dann `proxy_pass` ins Labor.
  4. Das Cookie gilt nur für `<host>:8443` – Cookies trennen nicht nach Port, aber das Cookie heißt anders als alles
     im echten HydraHive und öffnet dort nichts. `Cookie`-Kopf wird beim Weiterreichen an die Probe auf das
     Probe-eigene beschränkt (das Labor-Cookie wird entfernt).

## Gemessen (hydratest, 30.10. abends, Labor 2 CPU / 4 GB)

- `npm run build` im Labor: **15 s**, `dist` **90 MB**. Kern-Backend im Labor mit eigenen Daten: startet in ~10 s,
  `/api/health` ok. Nichts nachinstalliert – venv und Node aus L1 reichen.
- Oberfläche: im echten Server liefert **nginx** `frontend/dist` aus, nicht das Backend → die Probe braucht im Labor
  einen kleinen Auslieferer für `dist` + `/api`-Weiterleitung (Kern-Backend allein liefert keine Oberfläche).
  Plan: ein **winziges Python-Skript** im Modul (statisch `dist`, `/api` und WebSocket an `127.0.0.1:8002`), läuft
  als `labor`, lauscht auf `0.0.0.0:8001`. Kein nginx im Labor nötig.
- **Eingehende Regel** `ingress allow source=<Gateway>/32 protocol=tcp destination_port=8001`: Server → Labor:8001
  **200**, andere Ports zu. Aus dem Labor bleiben Gateway (443/8001), Server, Router, `.2` **zu**, Internet offen.
  Messung danach wieder entfernt.

## Umgesetzt (0.3.0, 30./31.10.)

- **Auslieferer** `probe/front.py` (im Labor, als `labor`, root-eigen unter `/opt/hh-labor-probe`, vom Labor-Agenten
  nicht änderbar): `dist` + `/api` gestreamt an das Probe-Backend `127.0.0.1:8002`.
- **Probe-Dienste** per `systemd-run` im Container, beide als `labor`; eigene Daten unter `/work/.probe`
  (Schlüssel + Admin-Passwort beim ersten Bau, 0600). Discord/WhatsApp/Mail/Teamchat/Update-Check/AgentLink aus,
  Modul-Hub = Labor-Ordner.
- **Anmeldung** wie geplant (Ticket 60 s → Cookie 8 h → `auth_request`). Ticket-Einlösen und Prüfung laufen über den
  Geräte-Weg des Kerns (`/api/module-device/hydralabor/…`, ohne HydraHive-Login, mit Bremse je Adresse); nginx merkt
  sich ein gültiges Ergebnis 30 s je Cookie.
- **nginx :8443**: nur Heimnetz/Tailscale, keine Cookies an die Probe, keine `Set-Cookie` von der Probe (Cookies
  trennen nicht nach Port), CSP `connect-src 'self'` / `form-action 'self'`, Rücknahme bei `nginx -t`.
- Freigabe + nginx erst, **wenn die Probe antwortet**; Stoppen, Zurücksetzen und Entfernen räumen nginx-Block,
  eingehende Regel und Zwischenspeicher ab (nur was im Zustand steht).

## Echt geprüft (hydratest, 30./31.10.)

- Bau 15–21 s, Start 3–6 s. Browser: „Probe öffnen“ → neuer Tab auf :8443 → Anmeldeseite der Probe → mit den
  angezeigten Daten angemeldet. Änderung im Labor → „Neu bauen“ → sofort in der Probe sichtbar.
- Ohne Cookie, mit falschem Cookie, mit dem Login des echten HydraHive: 401. Ticket zweimal: 401. Probe-Cookie am
  echten HydraHive: 401. Im Browser nur das Probe-Cookie; die Probe sieht die Anmeldung des echten HydraHive nicht.
- Aus dem Labor bleiben Server (443/8001/8443/22), Router, `.2` und `hhnat0` **zu**, Internet offen.
- Stoppen/Zurücksetzen/Entfernen: kein nginx-Block, keine Regel, kein Zwischenspeicher, Port 8443 zu.
- E2E 1600/1280/393/375 (Kasten + neuer Tab), ältere Labor-E2E grün.
- **Befund unterwegs:** `incus file push --create-dirs` legt den Ordner mit 0750 an → `labor` konnte den Auslieferer
  nicht lesen (nur im frischen Labor sichtbar). Ordner wird jetzt selbst mit 755 angelegt.

## Nicht getestet

- Zugriff von außerhalb des Heimnetzes (nur per `deny all` im Block abgesichert, nicht von außen gemessen).
- Server ohne Tailscale/mit öffentlicher IP (VPS), anderer Port als 8443, nicht-Ubuntu-Server.
- Module in der Probe installieren (Modulverwaltung der Probe zeigt auf den Labor-Ordner – nicht durchgeklickt).

## Nachträge 0.3.1 / 0.3.2 (Befunde Till auf .2, 31.10.)

- **0.3.1:** In der Probe fehlten alle Grafiken. Der Auslieferer gab nur `dist/assets/` heraus, Bilder aus `public/`
  liegen im Hauptordner von `dist`. Jetzt wie nginx: jede Datei aus `dist`, sonst `index.html`.
- **0.3.2:** Module ließen sich in der Probe nicht installieren oder aktualisieren. Kopieren und Bauen liefen durch,
  der Neustart fehlte: Der Kern schreibt `.restart_request`, auf dem Server startet `hydrahive2-restart.timer` dann
  neu. In der Probe gab es keinen Wächter. Jetzt `hh-probe-restart.path` (systemd-run, PathExists) → Backend neu.
  Echt geprüft: „Diagramme“ in der Probe installiert → Neustart von selbst → Modul geladen, Schnittstelle 200.
