# TV-Werkstatt: HydraHive-App auf Fernsehern und Tablets (G1–G4)

Anlass: Till möchte eine eigene HydraHive-App für Fernseher und Wand-Tablets („in jedes Zimmer ein Tablet an die Wand“).
Klick-Demo: `generated/tv-werkstatt/hydra-tv-demo.html`. Vorgabe 13.11.2026: „erst mal die app grundlage bauen“.

| Schritt | Inhalt |
|---|---|
| G1 Server-Seite (0.13.0) | Koppeln, Lebenszeichen, Meldungen vom Gerät, Einblendungen abholen, Bereich im Reiter Geräte |
| **G2 App-Gerüst (0.14.0)** | Android-App im Container gebaut (Muster cleanyourtv `addons/tv-inspector`), Code eintippen, verbunden |
| G3 Einblendung | Testmeldung aus der Werkstatt erscheint am Gerät, Antwort per Knopf zurück |
| G4 Aufspielen | App per Klick aus der Werkstatt auf eingetragene Fernseher bringen |

## Verbindung

Die App verbindet sich **vom Gerät zu Hydra**. Am Gerät läuft kein offener Dienst.

- Geräte-Routen hängen am Kern über `register_device_router` unter `/api/module-device/tvwerkstatt/app/…`.
  Sie brauchen kein Login. Der Kern begrenzt sie auf 240 Anfragen je Minute und Adresse, `app_auth` ist Pflicht.
  Ein Kern ohne `register_device_router` startet das Modul trotzdem, nur ohne Geräte-Routen (Warnung im Log).
- Hydras Zertifikat ist selbst ausgestellt, und der Name passt nicht zur Adresse (SAN ohne `.2`). Deshalb prüft die
  App den **Fingerabdruck des Schlüssels** (SPKI, `sha256/…`) statt des Namens. Die Werkstatt zeigt ihn mit dem Code an,
  aber nur für lokale Adressen (`app_tls.py`).

## Koppeln (`app_pairing.py`, Muster Modul mining)

1. Ein Admin gibt im Reiter Geräte einen Namen ein und klickt **Code erzeugen**. Der Code hat 12 Zeichen, gilt 15 min
   und nur einmal, gespeichert wird nur sein Hash. Angezeigt werden Server und Fingerabdruck.
2. Die App schickt den Code einmal an `POST /app/enroll` (Header `X-Pairing-Code`) und bekommt dafür einen eigenen
   Schlüssel `hhtvw_…`. Gespeichert wird nur sein SHA-256. Der Code ist danach verbraucht.
3. Alles Weitere läuft mit `Authorization: Bearer hhtvw_…`. Ein Gerät mit Schlüssel kann kein weiteres Gerät koppeln.
4. **Sperren** löscht den Schlüssel sofort (`token_hash = NULL`). Zusätzlich zählt nur `status = 'active'`.
   **Entfernen** geht erst nach dem Sperren.

## Geräte-Routen

| Route | Zweck |
|---|---|
| `POST /app/enroll` | Code gegen Schlüssel tauschen, Gerätedaten (Art, Modell, Android, App-Version; gekürzt) |
| `POST /app/hello` | Lebenszeichen mit Zustand, Antwort: Name und Takt (25 s) |
| `POST /app/events` | Meldung: `screen`, `foreground`, `input`, `playback`, `answer`, `hello`; höchstens 2000 Zeichen |
| `GET /app/notices?after=&wait=` | Einblendungen abholen, lange Abfrage höchstens 30 s, nur eigene |
| `POST /app/notices/{id}` | gezeigt bzw. beantwortet; die Antwort muss einer der angebotenen Knöpfe sein |

Aufbewahrt werden je Gerät die letzten 500 Meldungen und 200 Einblendungen. Ältere werden gekappt.

## Admin-Routen (Login, nur Admins)

`GET /app/devices`, `POST /app/pairing`, `POST /app/devices/{id}/revoke`, `DELETE /app/devices/{id}`,
`POST /app/devices/{id}/notices` (Testmeldung, höchstens 3 Knöpfe zu je 20 Zeichen), `GET /app/devices/{id}/activity`.

## G2 App-Gerüst (0.14.0)

Danach klickbar: Im Reiter Geräte **App bauen**, danach **App herunterladen** (für Tablets zum Aufspielen von Hand). In
der App Server und Code eintippen, Fingerabdruck vergleichen, dann steht dort „Verbunden als <Name>“ und die Werkstatt
zeigt das Gerät als verbunden.

**Quelltext im Modul:** `android/hydra-app/` (Java, ohne Bibliotheken; Muster cleanyourtv `addons/tv-inspector`:
AGP 8.5.2, compileSdk 34). Paket `io.hydrahive.app`, `minSdk 21` (alte Tablets), einziges Recht `INTERNET`,
`allowBackup=false`. Startet auf Fernsehern (Leanback) und Tablets (normaler Starter). Eine Seite:
1. Einrichten: Server (vorbelegt `https://`) und Code.
2. Bei lokaler Adresse: Die App liest den Schlüssel des Servers und zeigt einen **kurzen Fingerabdruck**
   (12 Hex-Zeichen, z. B. `3FA2 91C0 7B1E`). Die Werkstatt zeigt denselben neben dem Code. Erst nach „Stimmt“ wird
   gekoppelt, danach prüft die App nur noch genau diesen Schlüssel. Bei öffentlicher Adresse gilt die normale Prüfung.
3. Gekoppelt: Name, „verbunden“ / „nicht verbunden“, Lebenszeichen alle 25 s, solange die App offen ist.
   Ein abgelehnter Schlüssel (401) führt zurück zum Einrichten.
Reine Logik (Adresse prüfen, lokal oder nicht, Code säubern, kurzer Fingerabdruck) steht in eigenen Klassen mit
JUnit-Tests.

**Bau im Container** (Auftrag `app_build`, Muster Startbildschirm): Container an → cleanyourtv am festen Stand holen
und den Gradle-Wrapper prüfen (wie bisher) → Quelltext der App als tar über stdin nach `~/src/hydra-app` → Bau mit dem
geprüften Wrapper (`launcher/gradlew -p …`), vorher die JUnit-Tests → Auswertung: Paket `io.hydrahive.app`, Signatur
= Schlüssel des Containers, Rechte genau `INTERNET` → App (höchstens 5 MB) nach `data_dir/tvwerkstatt/app/` holen,
Prüfsumme vergleichen → Container aus. Bau-Eintrag mit `part = hydra-app`, Stand = Prüfsumme des Quelltexts.

**Routen (Admin):** `POST /app/build`, `GET /app/apk` (zuletzt gebaute App). `POST /app/pairing` liefert zusätzlich
`pin_short`.

**Nicht in G2:** Einblendungen anzeigen (G3), Dienst im Hintergrund, Aufspielen per Klick (G4), eigener
Signierschlüssel (vorerst der des Containers wie beim Startbildschirm).

## Bewusst nicht in G1

Keine Sprache und kein Mikro, keine Befehle an das Gerät (App öffnen, Eingang), kein Weiterreichen an Home Assistant
oder Agenten. Die Meldungen werden nur gespeichert und sind über `activity` abrufbar; die Oberfläche zeigt in G1
nur verbunden/nicht verbunden. Keine App (G2).
