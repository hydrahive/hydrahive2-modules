# Mediacenter — Konfiguration

Alle externen Adressen kommen aus Umgebungsvariablen. **Im Code steht keine
Adresse und keine IP** — ein Umzug ist eine Konfigurationsänderung, kein
Code-Eingriff. Zwei Tests wachen darüber
(`tests/test_configurable_endpoints.py`).

## Wo wird was eingestellt?

**Eine Regel:** Adresse *und* Schlüssel jedes Dienstes stehen zusammen in
**einem Credential**. Die Adresse gehört ins Feld URL/Muster. Das Mediacenter
liest beides von dort — es gibt keinen zweiten Ort.

Der Bereich **Einstellungen** im Mediacenter zeigt für jeden Dienst, ob er
eingerichtet und erreichbar ist, mit welcher Version er antwortet und welches
Credential dahintersteckt. Dort wird nichts eingegeben, nur angezeigt und zum
Credential-Store verlinkt.

Die Umgebungsvariablen unten sind **optional**. Sie schränken nur ein: ist eine
gesetzt, muss das Credential dazu passen. So kann ein Betreiber eine Instanz
serverseitig festnageln. Für den normalen Betrieb braucht man sie nicht.

## Umgebungsvariablen (optional)

| Variable | Zweck | Default |
|---|---|---|
| `HH_MEDIACENTER_INDEXER_ORIGIN` | Newznab-Indexer | `https://treasure-maps.com` |
| `HH_MEDIACENTER_INDEXER_FILE_HOST` | Dateihost für NZB-Downloads | `file.<indexer-host>` |
| `HH_MEDIACENTER_COVER_HOSTS` | Bildhosts für Cover (kommagetrennt) | `picbit.io,cdn.<indexer>,<indexer>` |
| `HH_MEDIACENTER_SAB_ORIGIN` | SABnzbd — erlaubte Adresse | *(leer → Adresse aus dem Credential)* |
| `HH_MEDIACENTER_RADARR_ORIGIN` | Radarr — erlaubte Adresse | *(leer → aus dem Credential)* |
| `HH_MEDIACENTER_SONARR_ORIGIN` | Sonarr — erlaubte Adresse | *(leer → aus dem Credential)* |

### Warum die Defaults leer sind

Ein Default auf eine fremde Adresse würde bedeuten, dass eine frische
Installation ungefragt versucht, irgendwo im Netz Dienste anzusprechen.

Bei Radarr/Sonarr gilt dasselbe Muster wie bei SABnzbd: ohne Variable stammt
die Adresse aus dem Credential. Ist kein Credential hinterlegt, bleibt die
Funktion einfach aus — Suche und Downloads laufen davon unberührt weiter.

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
