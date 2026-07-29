# Spec: Voice-Onboarding — „Box an USB → Firmware → WLAN → funktioniert"

**Stand:** 2026-07-29 · **Status:** Design (Brainstorming), noch nicht implementiert
**Referenz:** Home-Assistant-Voice-PE-Onboarding · verwandt: `PROJEKTPLAN-multibox-wakeword.md` (Wake-Words, komplementär)

---

## Problem

Heute erwartet ein Kunde: **Modul installieren → Voice-Box einrichten wie in Home
Assistant → benutzen.** Tatsächlich bekommt er „Die Voice-Bridge ist nicht
erreichbar". Grund: Der Voice-Assistent besteht aus zwei Teilen, von denen nur
einer per Update kommt.

- **Voice-Modul** (Cockpit-UI, `hydrahive2-modules/voice`, v0.7.0) — kommt per
  Install, ist aber nur ein **Proxy** an `127.0.0.1:8898`.
- **Voice-Bridge** (`voice-pe/bridge/`) — separater Python-Dienst, der die Box
  über die ESPHome-API anwählt. Läuft als systemd-Unit mit **hardgecodetem
  Workspace-Pfad**, bindet die Box über **`wifi_secret.env`** (`DEVICE_IP`,
  `API_NOISE_KEY`, `OWNER_USER`), **eine Bridge pro Box**. Manuell mit root
  einzurichten. → für einen Kunden nicht machbar.

## Ausgangslage (verifiziert 2026-07-29)

**Gute Nachricht — der schwierigste Teil ist schon da:**
- Bridge spricht bereits das **native ESPHome-Protokoll** (`aioesphomeapi`,
  `subscribe_voice_assistant`, `noise_psk`) — exakt wie HA.
- Eigene Firmware **`build/hydra-voice.yaml`** ist gebaut (ESPHome, micro-mp3/opus,
  **mdns** ist bereits als Komponente drin).
- Box-Port 6053 (ESPHome-API), Bridge-Control 8898, Audio-HTTP 8899.

**Was fehlt, ist nicht das Protokoll, sondern das Onboarding drumherum.**

## Wie Home Assistant es macht (Referenz-Flow)

1. Box per **USB-C an den PC** (nicht an den Server).
2. **Firmware flashen im Browser** über ESPHome-Web-Installer (**WebSerial**,
   läuft im Chrome/Edge des Nutzers, keine Software-Installation).
3. **WLAN einrichten** über **Improv** (Serial/BLE-Provisioning) — Installer
   fragt SSID+Passwort, schiebt sie auf die Box.
4. Box verbindet sich ins WLAN und **meldet sich per mDNS** (`_esphomelib._tcp`).
5. Server zeigt „Neues Gerät gefunden" → ein Klick zum Übernehmen.

Kern: HA **lauscht**, Boxen **melden sich**. Ein Server-Endpunkt für **alle**
Geräte. Kein Prozess-pro-Box.

## Architektur-Entscheidung (getroffen): ESPHome-nativ ausbauen

Da die Bridge bereits `aioesphomeapi` nutzt und die Firmware ESPHome ist, wird
der **ESPHome-Weg** ausgebaut (nicht ein eigenes Protokoll gebaut). Das nutzt
den funktionierenden Kern und das ganze ESPHome-Ökosystem (Web-Flasher, OTA,
mDNS, Improv). Der Umbau betrifft die **Verbindungsrichtung + das Onboarding**,
nicht das Protokoll.

---

## Die drei Lücken

| # | Lücke | HA-Lösung | HydraHive-Umbau |
|---|-------|-----------|-----------------|
| L1 | **Verbindungsrichtung** | mDNS: Box meldet sich | Bridge von „1 Prozess/Box, IP in .env" → **ein Dienst, der Geräte per mDNS entdeckt + N Boxen hält** (Geräte-Registry) |
| L2 | **Flashen** | gehosteter Web-Installer | Cockpit-Seite verlinkt auf **ESPHome-Web-Installer** mit `hydra-voice`-Firmware (WebSerial im Browser des Kunden!) |
| L3 | **WLAN + Registrierung** | Improv + Auto-Discovery-Dialog | **Improv** im Flash-Flow + „Gerät gefunden/koppeln"-UI im Cockpit (inkl. `noise_psk`-Übernahme) |

---

## MVP-Schnitt (bewusst gestuft — nicht alles auf einmal)

### Stufe 0 — Ehrlichkeit sofort (klein, unabhängig)
Solange kein Gerät gekoppelt ist, zeigt die Voice-Seite eine **freundliche
Einrichtungs-Ansicht** („Noch keine Voice-Box eingerichtet — so geht's…") statt
der technischen Fehlermeldung „Bridge-Dienst läuft nicht?". Kein Architektur-
umbau, reine UX. → sofort umsetzbar, entschärft den Kunden-Frust.

### Stufe 1 — Multi-Device-Bridge + Geräte-Registry (Kern-Umbau, L1)
- Datenmodell **Box** (id, name, host/ip, noise_psk, owner_user, room, wake_word,
  state). Persistenz analog Modul-Daten (nicht hardgecodete .env).
- Bridge wird **Multi-Device**: hält N ESPHome-Verbindungen, ein Control-API-
  Endpunkt statt Port-pro-Box. Watchdog/systemd = **eine** Unit, pfad-entkoppelt.
- Cockpit: Geräte-Liste, Box manuell hinzufügen (**IP + noise_psk eingeben**) —
  das ist der ehrliche MVP für „funktioniert", auch ohne Auto-Discovery.

### Stufe 2 — mDNS-Auto-Discovery (L1 komplett)
- Bridge/Server lauscht auf `_esphomelib._tcp` → neue Boxen erscheinen im
  Cockpit als „gefunden", Kunde klickt „koppeln" (statt IP tippen).

### Stufe 3 — Web-Flasher + WLAN-Provisioning (L2+L3, das volle HA-Erlebnis)
- Cockpit-Seite „Neue Box einrichten": WebSerial-Flasher (eigene gehostete
  Installer-Seite mit `hydra-voice`-Manifest) + Improv-WLAN.
- Danach greift Stufe 2 (Discovery) automatisch → echtes Plug-and-Play.

### Stufe 4 — Politur
- OTA-Updates aus dem Cockpit, Wake-Word-Zuweisung pro Box (Brücke zum
  Multibox-Plan), Raum-/Owner-Zuordnung, Box umbenennen/entfernen.

---

## Zentrale offene Frage (vor Stufe 3)

**Wie weit Richtung „HA-Klon"?** Stufe 1+2 (Discovery + manuell koppeln) liefern
schon „Box taucht auf und funktioniert". Stufe 3 (Web-Flasher + Improv) ist das
volle Plug-and-Play, aber deutlich mehr Arbeit (WebSerial-Frontend, gehosteter
Installer, Improv-Flow). Entscheidung: MVP bei Stufe 1-2 stoppen und Flashen
vorerst dokumentiert-manuell (ESPHome-Installer-Link) lassen, oder gleich bis
Stufe 3 durchziehen?

## Sicherheit
- `noise_psk` pro Box ist ein Secret → verschlüsselt/`0600` speichern, nie im
  Klartext ins Frontend zurückgeben, nie loggen.
- Box-Zuordnung an `owner_user` (Multi-User, wie heute OWNER_USER).
- Flash/Provisioning läuft im **Browser des Kunden** (WebSerial) — der Server
  bekommt die Box-Zugangsdaten erst beim Koppeln.

## Nicht in dieser Spec
- Wake-Word-Training/-Auswahl → eigener Plan `PROJEKTPLAN-multibox-wakeword.md`.
- STT/TTS-Deployment (Container) → bestehend.

## Akzeptanzkriterien (Gesamt-Ziel)
1. Kunde installiert Voice-Modul → sieht eine sinnvolle Einrichtungs-Ansicht,
   keine kryptische Fehlermeldung. (Stufe 0)
2. Kunde kann eine Box im Cockpit hinzufügen und danach per Sprache nutzen,
   ohne systemd/.env von Hand anzufassen. (Stufe 1)
3. Eine ins WLAN gebrachte Box erscheint automatisch im Cockpit. (Stufe 2)
4. Optional: Kunde flasht + WLAN-provisioniert die Box aus dem Browser. (Stufe 3)
5. Mehrere Boxen je Server/User laufen parallel und stabil.
