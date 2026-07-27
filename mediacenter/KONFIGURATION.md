# Mediacenter — Konfiguration

Alle externen Adressen kommen aus Umgebungsvariablen. **Im Code steht keine
Adresse und keine IP** — ein Umzug ist eine Konfigurationsänderung, kein
Code-Eingriff. Zwei Tests wachen darüber
(`tests/test_configurable_endpoints.py`).

## Umgebungsvariablen

| Variable | Zweck | Default |
|---|---|---|
| `HH_MEDIACENTER_INDEXER_ORIGIN` | Newznab-Indexer | `https://treasure-maps.com` |
| `HH_MEDIACENTER_INDEXER_FILE_HOST` | Dateihost für NZB-Downloads | `file.<indexer-host>` |
| `HH_MEDIACENTER_COVER_HOSTS` | Bildhosts für Cover (kommagetrennt) | `picbit.io,cdn.<indexer>,<indexer>` |
| `HH_MEDIACENTER_SAB_ORIGIN` | SABnzbd — erlaubte Adresse | *(leer → Adresse aus dem Credential)* |
| `HH_MEDIACENTER_RADARR_ORIGIN` | Radarr | *(leer → deaktiviert)* |
| `HH_MEDIACENTER_SONARR_ORIGIN` | Sonarr | *(leer → deaktiviert)* |

### Warum manche Defaults leer sind

Bei Radarr/Sonarr bedeutet leer **bewusst „nicht konfiguriert"**. Ein Default
auf eine fremde Adresse würde bedeuten, dass eine frische Installation
ungefragt versucht, irgendwo im Netz Dienste anzusprechen.

Bei `HH_MEDIACENTER_SAB_ORIGIN` gilt: ohne Angabe stammt die Adresse aus dem
`url_pattern` des Credentials `sabnzb_token` — der Nutzer pflegt sie dort
ohnehin. Ist die Variable gesetzt, muss das Credential dazu passen; so kann ein
Betreiber die erlaubte Instanz serverseitig festnageln.

> **Historie:** Vorher stand hier eine konkrete IP als Default im Code. Sie
> einfach zu löschen hätte den laufenden Betrieb abgeschaltet, weil die
> Variable nirgends gesetzt war — daher der Weg über das Credential.

## Zugangsdaten

Die API-Schlüssel gehören in den Credential-Store, **nicht** in
Umgebungsvariablen. Jeder Eintrag trägt seine Adresse im `url_pattern`.

| Credential | Dienst |
|---|---|
| `tresuere_token` | Newznab-Indexer |
| `sabnzb_token` | SABnzbd |
| `radarr_token` | Radarr |
| `sonarr_token` | Sonarr |

## Einrichtung per systemd

Adressen als Drop-in ablegen, damit sie ein Update überleben:

```ini
# /etc/systemd/system/hydrahive2.service.d/mediacenter.conf
[Service]
Environment=HH_MEDIACENTER_SAB_ORIGIN=http://<host>:<port>
Environment=HH_MEDIACENTER_RADARR_ORIGIN=http://<host>:<port>
Environment=HH_MEDIACENTER_SONARR_ORIGIN=http://<host>:<port>
```

Danach `systemctl daemon-reload && systemctl restart hydrahive2`.

Die Schlüssel selbst kommen über die HydraHive-Oberfläche in den
Credential-Store — niemals in diese Datei.
