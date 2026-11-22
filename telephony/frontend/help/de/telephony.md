# VoIP – dein Telefonassistent an der FRITZ!Box

VoIP verbindet HydraHive mit deiner FRITZ!Box oder einer anderen SIP-Anlage. HydraHive meldet sich dort wie ein
IP-Telefon an, nimmt Anrufe mit einer Ansage oder dem KI-Telefon-Assistenten an und ruft auf Knopfdruck selbst an.
Das Modul ist noch in Entwicklung – einige Bereiche zeigen schon ihren Platz, haben aber noch keinen Inhalt.

## So startest du

1. Öffne in der Seitenleiste **VoIP**. Du landest in der **Übersicht**.
2. Klicke auf **Jetzt einrichten** – das öffnet den Reiter **Einstellungen**.
3. Lege in der FRITZ!Box ein IP-Telefon an. Die **Anleitung: HydraHive an der FRITZ!Box anmelden** steht unten auf
   der Einstellungsseite Schritt für Schritt (Telefonie → Telefoniegeräte → „Neues Gerät einrichten“ → „LAN/WLAN
   (IP-Telefon)“). Benutzername und Kennwort brauchen je mindestens 8 Zeichen.
4. Wähle bei **Anlage** „FRITZ!Box“ (oder **Andere SIP-Anlage**), trage die **Adresse der Anlage** (z. B. fritz.box),
   den **Benutzername** und das **Kennwort** ein und klicke **Speichern**, dann **Verbinden**.
5. Steht beim Status **Verbunden**, ist HydraHive angemeldet – und bleibt es auch nach einem Neustart.

## Was du damit machen kannst

### Übersicht
Zeigt den Verbindungsstatus und was das Modul heute kann. Von hier kommst du mit **Jetzt einrichten** bzw.
**Einstellungen öffnen** zur Einrichtung.

### Einstellungen
- **Verbindung zur Telefonanlage**: Anlage, Adresse, Benutzername, Kennwort und optional die **Eigene Rufnummer (optional)**.
  Das Kennwort wird verschlüsselt gespeichert und nie wieder angezeigt. Unter **Erweitert (Ports)** lassen sich die
  Ports ändern – nur nötig, wenn ein Router zwischen FRITZ!Box und HydraHive liegt.
- **Anrufe annehmen**: Mit dem Schalter legst du fest, ob HydraHive abnimmt. Ist er aus, lehnt HydraHive ab und andere
  Telefone derselben Rufnummer klingeln weiter.
- **Was passiert bei einem Anruf?**
  - **Nur Ansage**: HydraHive nimmt ab, spricht die **Ansage** und legt auf. Die Ansage liest die lokale
    Sprachausgabe vor, höchstens 500 Zeichen; leer bedeutet die Vorgabe.
  - **Telefon-Assistent (KI)**: Ein KI-Assistent nimmt das Anliegen auf und beantwortet Fragen. Unter
    **Für wen spricht der Assistent?** trägst du den Namen für die Begrüßung ein, unter
    **Was der Assistent wissen darf** einen Wissenstext (höchstens 4000 Zeichen). Was dort nicht steht, gibt er weiter, statt zu raten. Das **Sprachmodell**
    ist wählbar.
- **Testanruf starten**: HydraHive nimmt in den nächsten 60 Sekunden genau einen Anruf an – auch wenn der Schalter aus
  ist. Danach fragt HydraHive, ob du die Ansage gehört hast.
- **Letzte Anrufe**: Liste mit Richtung, Ergebnis und – beim Assistenten – einer Notiz. Neue Notizen kannst du
  **Als gelesen markieren**; manche sind markiert mit „Bitte ansehen – ungewöhnliches oder sensibles Anliegen.“

### Telefonaufträge
Hier rufst du selbst an (erst nach dem Verbinden). Unter **Was soll beim Anruf passieren?**:
- **Ansage vorlesen**: HydraHive liest deinen Text vor und legt auf – die Gegenseite kann nicht antworten.
  Knopf: **Anrufen & Ansage vorlesen**.
- **Assistent führt das Gespräch**: Du gibst einen **Auftrag** ein (z. B. einen Termin erfragen) und optional, was er
  über dich nennen darf (**Darf nennen (optional)**). Der Assistent stellt sich als KI vor, macht keine Zusagen und
  schreibt danach eine Notiz. Knopf: **Anrufen mit Assistent**.
- **Auflegen** beendet den laufenden Anruf.
- Unter **Letzte Anrufe** gibt es bei Notizen mit Rückrufnummer den Knopf **Zurückrufen**.
- **Freigaben**: **Sondernummern erlauben (0900, 0137, 0180, Auskunft 118 …)** und **Auslandsnummern erlauben** sind standardmäßig aus, weil diese Nummern
  teuer werden können.

### Gespräche, Archiv, Telefon-Agent, Mitglieder
Diese Reiter sind schon sichtbar, zeigen aber noch keinen Inhalt („Dieser Bereich folgt in einer der nächsten
Versionen.“).

### Im Butler
Im Butler gibt es den Auslöser **Anruf kommt rein** (optional nur für bestimmte Nummern), die Bedingung
**Anrufer-Nummer** und die Aktionen **Mit Assistent annehmen**, **Mit Ansage annehmen**, **Anruf ablehnen**,
**Besetzt** und **Wie in den Einstellungen**. Abläufe im Butler gehen den Einstellungen vor.

## Gut zu wissen

- Wer darf das? VoIP einzurichten ist standardmäßig nur Admins erlaubt. Sonst erscheint „Du darfst VoIP nicht
  einrichten. Bitte einen Admin fragen.“
- Nur im eigenen Netz: Als Anlage sind nur Adressen im Heimnetz erlaubt (z. B. fritz.box oder 192.168.x.x).
  Gib niemals SIP-Ports der FRITZ!Box ins Internet frei.
- Grenzen beim Anrufen: Notrufnummern (110, 112) und FRITZ!Box-Codes werden nie gewählt. Höchstens 20 Anrufe pro
  Tag. Nur du löst einen Anruf aus – Agenten können (noch) nicht selbst anrufen.
- Datenschutz beim Assistenten: Anrufer sind Fremde. Der Assistent hat keine Werkzeuge und keinen Zugriff auf
  Dateien, Mails oder Projekte, sagt am Anfang, dass eine KI spricht, und speichert weder Ton noch Wortlaut – nur die
  Notiz. Am Telefon dauert eine Antwort meist 3–4 Sekunden.
- Typische Meldungen: **Benutzername oder Kennwort falsch** (in der FRITZ!Box beim IP-Telefon unter
  „Anmeldedaten“ prüfen), **Anlage antwortet nicht** (Adresse, Port, Benutzername prüfen), **Adresse nicht erlaubt**
  (nur Heimnetz), **Lokaler Port belegt** (unter „Erweitert“ einen anderen wählen).
- Router dazwischen? Hört man bei „Verbunden“ im Gespräch nichts, liegt es meist am Router: Ports weiterleiten
  und „SIP-ALG“ ausschalten. Die Einzelheiten stehen auf der Einstellungsseite.

*Stand: VoIP 0.13.1, 22.11.2026*
