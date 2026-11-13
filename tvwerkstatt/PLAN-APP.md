# TV-Werkstatt: HydraHive-App auf Fernsehern und Tablets (G1–G4)

Anlass: Till möchte eine eigene HydraHive-App für Fernseher und Wand-Tablets („in jedes Zimmer ein Tablet an die Wand“).
Klick-Demo: `generated/tv-werkstatt/hydra-tv-demo.html`. Vorgabe 13.11.2026: „erst mal die app grundlage bauen“.

| Schritt | Inhalt |
|---|---|
| **G1 Server-Seite (0.13.0, dieser Stand)** | Koppeln, Lebenszeichen, Meldungen vom Gerät, Einblendungen abholen, Bereich im Reiter Geräte |
| G2 App-Gerüst | Android-App im Container gebaut (Muster cleanyourtv `addons/tv-inspector`), Code eintippen, verbunden |
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

## Bewusst nicht in G1

Keine Sprache und kein Mikro, keine Befehle an das Gerät (App öffnen, Eingang), kein Weiterreichen an Home Assistant
oder Agenten. Die Meldungen werden nur gespeichert und sind über `activity` abrufbar; die Oberfläche zeigt in G1
nur verbunden/nicht verbunden. Keine App (G2).
