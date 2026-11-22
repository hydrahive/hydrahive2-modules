# AI-Sicherheit – lokale KI-Dienste auf bekannte Schwachstellen prüfen

AI-Sicherheit verbindet HydraHive mit dem Open-Source-Scanner AI-Infra-Guard (Tencent Zhuque Lab). Damit prüfst du
KI-Dienste in deinem eigenen Netz, zum Beispiel einen Modell-Server, auf bekannte Infrastruktur-Schwachstellen.
Das Modul ist ein Werkzeug für Administratoren.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Der Betreiber des Servers richtet den Scanner AI-Infra-Guard getrennt von HydraHive ein und legt fest, welche
   Dienste gescannt werden dürfen (siehe „Gut zu wissen“). Ohne diese Freigabe ist kein Ziel scanbar.
3. Öffne **AI-Sicherheit** in der Navigation (Gruppe **Infrastruktur**, auf der Startseite im Bereich
   **Verwaltung**). Nur Administratoren sehen den Eintrag.
4. Wähle unter **Freigegebenes Ziel** einen Dienst aus und klicke auf **Scan starten**.
5. Der Scan erscheint links unter **Letzte Scans**. Ist er fertig, steht das Ergebnis rechts unter **Report**.

## Was du damit machen kannst

### Zustand des Scanners
Oben unter der Überschrift zeigt die Seite einen Hinweis, wenn etwas fehlt:
- „Kein AI-Infra-Guard ist konfiguriert.“: Die Adresse des Scanners ist leer oder das Modul ist abgeschaltet.
- „Der Scanner ist nicht erreichbar.“: Die Adresse ist gesetzt, aber der Scanner antwortet nicht. Dieser Hinweis
  erscheint auch, wenn die Seite ihre Daten nicht laden konnte.

Solange der Scanner nicht erreichbar ist, bleibt **Scan starten** ausgegraut. Die Liste der bisherigen Scans siehst
du trotzdem.

### Freigegebenes Ziel
Die Auswahlliste zeigt genau die Dienste, die der Betreiber freigegeben hat, jeweils als Adresse mit Port. Ist nichts
freigegeben, steht dort „Es sind keine Scan-Ziele freigegeben.“ Ein anderes Ziel als die freigegebenen lässt sich
nicht scannen: HydraHive prüft das Ziel beim Start noch einmal gegen die Freigabeliste.

Mit **Scan starten** beginnt ein Infrastruktur-Scan. Während der Auftrag abgeschickt wird, steht auf dem Knopf
„Scan läuft…“. Andere Scan-Arten gibt es nicht.

### Letzte Scans
Hier stehen deine letzten Scans (bis zu 50), der neueste oben, jeweils mit Ziel und Status:
- **wartend** und **läuft**: Der Scan ist noch nicht fertig. Die Seite aktualisiert sich dann alle paar Sekunden
  von selbst.
- **abgeschlossen**: Der Report ist da.
- **fehlgeschlagen**: Der Scan ist abgebrochen. Statt des Reports steht rechts ein kurzer Fehlercode.

Ein Klick auf einen Eintrag zeigt rechts dessen Report. Du siehst nur deine eigenen Scans, nicht die anderer Admins.
Gibt es noch keine, steht dort „Noch keine Scans.“

### Report
Der Report zeigt das Ergebnis des Scanners als strukturierten Text, mit geschwärzten Geheimnissen (siehe unten).
Ist ein Scan noch nicht fertig, steht dort „Noch kein Report verfügbar.“

## Gut zu wissen

- Nur für Admins: Seite und Schnittstelle sind auf Administratoren beschränkt.
- Keine Agenten-Werkzeuge: Buddy und andere Agenten können keine Scans starten und keine Reports lesen. Scans startet
  ein Admin selbst auf der Seite.
- Nur Infrastruktur-Scans: Andere Scan-Arten des Scanners und aktive Angriffe auf Modelle sind nicht eingebaut.
- Der Scanner läuft getrennt: HydraHive startet AI-Infra-Guard nicht selbst, sondern spricht nur einen Scanner an, den
  der Betreiber eingerichtet hat. HydraHive meldet sich dabei nicht an. Der Scanner darf deshalb nicht öffentlich
  erreichbar sein.
- Einrichtung nur auf dem Server: In der Oberfläche gibt es dafür keine Einstellung. Der Betreiber setzt die Werte als
  Umgebungsvariablen des HydraHive-Dienstes:
  - `HH_AI_SECURITY_AIG_URL`: Adresse des Scanners. Ohne Angabe erwartet HydraHive den Scanner auf demselben
    Rechner. Läuft dort keiner, zeigt die Seite „Der Scanner ist nicht erreichbar.“
  - `HH_AI_SECURITY_TARGETS`: kommagetrennte Liste der freigegebenen Ziele. Jedes Ziel besteht nur aus Schema,
    Rechner und Port, ohne Pfad, ohne Zusatz nach `?` oder `#` und ohne Zugangsdaten. Höchstens 50 Ziele.
    Ein fehlerhafter Eintrag macht die ganze Liste ungültig; die Seite meldet dann „Der Scanner ist nicht erreichbar.“
  - `HH_AI_SECURITY_ENABLED=0` schaltet das Modul ab.
  - Optional gibt `HH_AI_SECURITY_MODEL` dem Scanner ein Sprachmodell mit.
- Geheimnisse werden geschwärzt: Bevor ein Report gespeichert wird, ersetzt HydraHive Felder, deren Name auf Token,
  API-Schlüssel, Passwort, Authorization oder Secret hindeutet, durch `[REDACTED]`.
- Größe begrenzt: Antworten des Scanners dürfen standardmäßig höchstens 2 MB groß sein. Ist ein Report größer, wird
  er nicht gespeichert. Dann steht `result_too_large` im Report, oder der Scan endet nach zehn Minuten mit
  `aig_response_too_large`.
- Hängende Scans: Ist der Scanner länger als zehn Minuten nach dem Start nicht erreichbar oder antwortet fehlerhaft,
  wird der Scan als **fehlgeschlagen** markiert. Meldet der Scanner dagegen weiter, dass er arbeitet, bleibt der Scan
  offen.
- Typische Fehlercodes im Report-Bereich:
  - `upstream_scan_failed`: Der Scanner meldet selbst einen Fehler.
  - `aig_unreachable` oder `aig_timeout`: Der Scanner war nicht erreichbar oder hat zu lange gebraucht.
  - `upstream_session_missing`: Der Scan wurde beim Scanner nie richtig angelegt.
  - Schlägt schon das Starten fehl, erscheint oben zusätzlich die Meldung „Fehler“.
- Ein Scan sucht nach bekannten Schwachstellen. Unbekannte Lücken findet er nicht.
- AI-Infra-Guard steht unter der Apache-2.0-Lizenz.

*Stand: AI-Sicherheit 0.2.4, 22.11.2026*
