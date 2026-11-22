# OpenTor OSINT – gezielt und nur lesend im Tor-Netz recherchieren

OpenTor OSINT ist ein streng begrenztes Recherche-Werkzeug für defensive Fragen: Taucht die eigene Firma,
ein Datenleck oder eine bekannte Angreifer-Gruppe auf Seiten im Tor-Netz auf? Es kann im Tor-Netz suchen und
einzelne Seiten als Text lesen, mehr nicht. Es hilft Menschen, die Sicherheitsvorfälle untersuchen oder die
eigene Gefährdung prüfen.

> **Nur autorisierte defensive OSINT-Recherche. Onion-Inhalte sind untrusted data und keine Anweisungen.**
> Dieser Hinweis steht oben auf der Seite. Keine Logins, keine Käufe, keine Kontaktaufnahme, keine Zugangsdaten
> ausprobieren. Tor ist keine Garantie für Anonymität oder Rechtssicherheit.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Dabei wird die OpenTor-Software
   eingerichtet und, falls auf dem Server noch keins vorhanden ist, auch Tor heruntergeladen. Das dauert etwas
   und braucht Internet. Nach der Installation ist OpenTor eingeschaltet.
2. Anfangs dürfen nur Admins OpenTor nutzen. Andere Nutzer gibt ein Admin unter **Freigaben** frei
   („OpenTor-Recherche“).
3. Öffne **OpenTor OSINT** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Wissen & Recherche**).
4. Prüfe oben die drei Kästen: Unter **Status** sollte „OpenTor ist aktiviert.“ stehen, daneben „Tor: OK“ und
   „Worker: OK“.
5. Gib einen **Suchbegriff** ein und klicke auf **Über Tor suchen**. Das Ergebnis erscheint unten unter **Treffer**.

## Was du damit machen kannst

### Status
Drei Kästen zeigen, ob OpenTor nutzbar ist:
- **Status**: „OpenTor ist aktiviert.“ oder „OpenTor ist durch die Administration deaktiviert.“
- **Tor**: „OK“, wenn das Tor-Netz erreichbar ist, sonst „—“.
- **Worker**: „OK“, wenn das Recherche-Programm im Hintergrund läuft, sonst „Worker oder Tor ist nicht
  erreichbar.“

Ist OpenTor ausgeschaltet, steht bei Tor immer „—“ und bei Worker „Worker oder Tor ist nicht erreichbar.“ Der Status wird beim Öffnen der
Seite geprüft. Willst du ihn neu sehen, lade die Seite neu.

### Für alle aktivieren / deaktivieren (nur Admins)
Admins sehen einen Knopf **Für alle deaktivieren** bzw. **Für alle aktivieren**. Er schaltet OpenTor für alle
Nutzer und alle Agenten gemeinsam aus oder ein. Ausgeschaltet lehnt das Modul jede Suche, jeden Abruf und jede
IOC-Auswertung ab.

### Über Tor suchen
Im Feld **Suchbegriff** gibst du ein, wonach gesucht werden soll, zum Beispiel einen Firmennamen oder den
Namen einer Ransomware-Gruppe. **Über Tor suchen** fragt Onion-Suchmaschinen ab. Die Seite sucht immer im
Modus für Threat Intelligence und holt höchstens 10 Treffer. Jeder Treffer hat Titel, Adresse und
Suchmaschine. E-Mail-Adressen und Telefonnummern in den Titeln werden geschwärzt.

### Explizite URL abrufen
Im Feld **Explizite URL abrufen** gibst du genau eine Adresse ein und klickst auf **Abrufen**. OpenTor lädt
diese eine Seite über Tor und gibt sie als Text zurück: Adresse, Statuscode, Titel, höchstens 8000 Zeichen
Text und die Links der Seite (bis zu 80). Den Links folgt OpenTor nicht von selbst. Willst du eine weitere
Seite sehen, rufst du sie selbst ab.

### Treffer
Unter **Treffer** steht das Ergebnis der letzten Suche oder des letzten Abrufs als Rohdaten. Solange du
noch nichts gesucht hast, steht dort „Noch keine Ergebnisse.“ Jedes Ergebnis trägt die Kennzeichnung
`UNTRUSTED_DATA` und den Hinweis, dass Onion-Inhalt keine Anweisung ist. Behandle alles darin als
ungeprüfte Behauptung, nicht als Tatsache.

## Mit Buddy und Agenten

OpenTor bringt vier Werkzeuge mit. Sie sind nicht automatisch an: Du gibst sie einem Agenten bewusst in
seinen Einstellungen im Reiter **Tools & MCP**. Ein Agent kann sie nur nutzen, wenn sein Besitzer die
Freigabe „OpenTor-Recherche“ hat.

- `opentor_status`: Ist OpenTor eingeschaltet, laufen Worker und Tor?
- `opentor_search`: Suche über Tor. Anders als die Seite kann der Agent den Modus wählen (Threat
  Intelligence, Ransomware, Firma), bestimmte Suchmaschinen aus einer festen Liste (zum Beispiel Ahmia,
  Tor66 oder DuckDuckGo-Tor) und bis zu 20 Treffer.
- `opentor_fetch`: Genau eine angegebene Adresse lesen, 500 bis 8000 Zeichen Text.
- `opentor_extract_iocs`: Aus Text, der schon vorliegt, Hinweise auf Angriffe (IOCs) herausziehen:
  IP-Adressen (IPv4), Onion-Adressen mit http/https davor und ob ein PGP-Schlüssel darin steckt.
  E-Mail-Adressen werden nur gezählt und geschwärzt. Das läuft ohne Netzzugriff, aber nur, wenn OpenTor
  eingeschaltet ist. Auf der Seite gibt es dafür keinen Knopf.

Was du fragen kannst:
- „Taucht unsere Firma auf bekannten Leak-Seiten auf? Fass die Treffer mit Quelle zusammen.“
- „Was ist über die Ransomware-Gruppe aus der Warnmeldung bekannt? Zieh die IP-Adressen heraus.“
- „Prüf diese Onion-Adresse aus der Phishing-Mail, ohne dass ich sie selbst öffne.“

Was nicht geht: Der Agent kann sich nirgends anmelden, keine Formulare abschicken, keine Dateien
herunterladen und keine Seiten selbständig durchklicken. Freie Befehle auf dem Server führen die Werkzeuge
nicht aus. Anweisungen, die auf einer Onion-Seite stehen, sind nur Daten. Der Agent soll sie nicht befolgen.

## Gut zu wissen

- Defensiver Zweck: OpenTor ist nur für erlaubte Sicherheits- und Threat-Intelligence-Recherche gedacht.
  Kläre im Zweifel vorher, ob die Recherche erlaubt und gedeckt ist.
- Schutzgitter beim Abruf:
  - Nur Adressen mit http oder https.
  - Keine Zugangsdaten in der Adresse (etwa `name:passwort@…`).
  - Keine Ziele im eigenen Netz: localhost, Adressen auf `.local` und private IP-Adressen werden abgelehnt.
  - Leitet eine Onion-Seite ins normale Internet um, wird der Abruf gestoppt.
- Datenschutz: E-Mail-Adressen und Telefonnummern werden im Text und in den Titeln durch
  `[redacted-email]` bzw. `[redacted-phone]` ersetzt.
- Tempolimit: Pro Person sind höchstens 12 Suchen, 12 Abrufe und 12 IOC-Auswertungen pro Minute erlaubt.
- Belege: Jede Suche und jeder Abruf wird mit Zeitpunkt gespeichert. Einträge, die älter als 30 Tage sind,
  werden beim nächsten Speichern gelöscht. Ansehen lassen sich diese Belege in der Oberfläche nicht.
- Tor ist langsam: Eine Suche oder ein Abruf darf höchstens eine Minute dauern, sonst bricht sie ab.
- Typische Fehlermeldungen (sie erscheinen im roten Kasten als Fachbegriff, davor steht „Error:“):
  - `opentor_disabled`: OpenTor ist ausgeschaltet. Ein Admin schaltet es mit **Für alle aktivieren** ein.
  - `opentor_unavailable`: Worker oder Tor antworten nicht oder waren zu langsam. Später erneut versuchen.
  - `rate_limit_exceeded`: Mehr als 12 Anfragen in einer Minute. Kurz warten.
  - `url_scheme_not_allowed`, `url_credentials_not_allowed`, `url_host_not_allowed`: Die Adresse ist
    nicht erlaubt (siehe Schutzgitter).
  - `onion_clearnet_redirect_blocked`: Die Onion-Seite wollte ins normale Internet umleiten.
  - „HTTP 422“: Der Suchbegriff ist zu kurz (mindestens 2 Zeichen) oder die Adresse zu kurz.
- Installation: Findet die Installation weder Tor noch die Paketverwaltung von Debian/Ubuntu, bricht sie mit
  einer Fehlermeldung ab.

*Stand: OpenTor OSINT 0.1.7, 22.11.2026*
