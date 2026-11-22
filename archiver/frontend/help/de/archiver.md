# Archiver – USB-Festplatten ins Projekt kopieren und zurück

Der Archiver ist ein Datenträger-Manager für USB-Laufwerke am Server. Er kopiert den Inhalt einer alten Festplatte in
ein Projekt oder ein ganzes Projekt auf eine Festplatte. Dazu kann er Laufwerke einhängen, ihren Zustand prüfen und
kaputte Dateisysteme reparieren. Er hilft allen, die alte Platten sichern oder Projekte auf eine Platte mitnehmen wollen.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Schließe die Festplatte per USB an den Server an.
3. Öffne den **Archiver** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Wissen & Recherche**).
4. Unter **Laufwerke** erscheint die Platte. Steht dort „nicht gemountet“, klicke auf **Mounten**. Danach klickst du
   die Platte an, um sie auszuwählen.
5. Unter **Archivieren** wählst du das Zielprojekt, gibst einen Namen für den Unterordner ein und klickst auf
   **HDD → Projekt**. Der Fortschritt erscheint unter **Jobs**.

## Was du damit machen kannst

Die Seite besteht aus Kästen, die du auf- und zuklappen kannst. **Diagnose**, **Reparatur** und **Exportieren** sind
am Anfang zugeklappt.

### Laufwerke
- Hier stehen alle USB- und Wechsel-Laufwerke mit Dateisystem, jeweils mit Name, Größe und Dateisystem-Typ.
  Ist keins da, steht dort „Kein USB-Laufwerk erkannt.“ Die festen Laufwerke des Servers erscheinen nicht.
- Der Pfeil-Knopf **Aktualisieren** oben rechts liest die Liste neu ein.
- **Mounten** hängt ein Laufwerk ein. Ist es eingehängt, gibt es zwei Knöpfe: **Remount** hängt es aus und sofort
  wieder ein. Der Stecker-Knopf **Sauber aushängen** hängt es aus, danach kannst du es abziehen.
- Ein Klick auf ein Laufwerk wählt es aus. **Diagnose**, **Reparatur** und **Archivieren** arbeiten mit diesem
  ausgewählten Laufwerk.

### Diagnose
- **SMART prüfen** fragt den Gesundheitszustand der Platte ab. Das Ergebnis lautet PASSED, FAILED oder UNKNOWN,
  darunter steht der vollständige Bericht. Kann die Platte das nicht, steht „(nicht verfügbar)“ dabei.
- **Fehlerlog (dmesg)** zeigt die Meldungen des Systems zu diesem Laufwerk, höchstens 200 Zeilen. Zeilen mit
  „error“ sind rot.
- Die Diagnose liest nur und verändert nichts an der Platte.

### Reparatur
- Bei NTFS-Platten (Windows) gibt es den Knopf **ntfsfix**, bei allen anderen den Knopf
  **fsck reparieren (ext2/3/4)**. fsck repariert gefundene Fehler ohne Rückfrage.
- Die Ausgabe der Reparatur läuft live mit. Am Ende steht „Fertig“ oder „Fehler“.
- Bei fsck hängt der Archiver das Laufwerk vorher selbst aus. Bei ntfsfix tut er das nicht, auch wenn der Hinweis in
  der Box es für beide ankündigt.
- **Abbrechen** beendet nur die Live-Anzeige. Die Reparatur selbst läuft im Hintergrund weiter.

### Archivieren
- Kopiert alles vom ausgewählten Laufwerk in einen Unterordner des gewählten Projekts.
- Ist kein Laufwerk ausgewählt, kannst du stattdessen einen Pfad von Hand eintragen.
- Wähle im Feld „Zielprojekt wählen…“ das Projekt und gib einen Unterordner-Namen ein, zum Beispiel
  HDD_2010_Blau. **HDD → Projekt** startet die Kopie.

### Exportieren
- Spiegelt den Projekt-Workspace auf das Laufwerk: Der ganze Inhalt des Projekts wird in einen Ordner auf der
  Platte kopiert.
- Wähle unter „Quell-Projekt wählen…“ das Projekt und unter „Ziellaufwerk wählen…“ ein eingehängtes Laufwerk. Gib
  einen Zielordner ein, zum Beispiel Backup_2026, und klicke auf **Projekt → HDD**.
- Was auf der Platte schon liegt, bleibt dort. Der Export löscht dort nichts, auch keine Dateien, die es im Projekt
  nicht mehr gibt.

### Jobs
- Der Kasten erscheint, sobald es Kopier-Aufträge gibt. Er zeigt deine eigenen Aufträge, die letzten 50.
- Jeder Auftrag zeigt die Richtung, die Zahl der kopierten Dateien, die Geschwindigkeit und einen Balken mit
  Prozent. Ein grüner Haken heißt fertig, ein rotes Kreuz fehlgeschlagen, ein graues Kreuz abgebrochen.
- Während ein Auftrag läuft, stoppt ihn das Kreuz (**Abbrechen**). Bei fertigen Aufträgen entfernt das Kreuz den
  Eintrag aus der Liste (**Eintrag löschen**). Gibt es mehr als einen fertigen Eintrag, räumt **Alle löschen** auf.
- Ließen sich einzelne Dateien nicht lesen, zum Beispiel wegen fehlender Rechte, zählt der Auftrag sie als
  „Fehler/Warnungen“. Der Auftrag gilt trotzdem als fertig.
- Bei fertigen Aufträgen gibt es **Nach Wallets suchen**. Das sucht in den kopierten Dateien nach Krypto-Wallets
  und Schlüsseldateien, etwa Bitcoin Core (wallet.dat), Monero, Electrum, Ethereum-Keystore sowie .key- und
  .pem-Dateien, und zeigt Fundort und Größe. Bei einem Export wird dabei das ganze Projekt durchsucht.

### Diagnose-Log
- Ganz unten klappst du **Diagnose-Log** auf. Es zeigt die letzten Meldungen des Archivers aus dem Systemprotokoll
  und aktualisiert sich alle 3 Sekunden, solange es offen ist.

## Gut zu wissen

- Rechte: Nach der Installation dürfen nur Admins den Archiver nutzen. Ein Admin kann das Recht
  „Archiver (Laufwerke, Kopier-Jobs)“ unter **Freigaben** an andere vergeben. Wer das Recht hat, arbeitet direkt
  mit den Platten am Server. Vergib es deshalb nur an Leute, denen du das zutraust.
- Erst **Sauber aushängen**, dann abziehen. Sonst können Daten auf der Platte kaputtgehen.
- Beim **Mounten** einer NTFS-Platte führt der Archiver vorher automatisch ntfsfix aus. Dabei verändert er die
  Platte ein wenig, damit sie sich einhängen lässt.
- Der Archiver prüft vor dem Kopieren nicht, ob am Ziel genug Platz ist.
- Wird HydraHive neu gestartet, während ein Auftrag läuft, wird der Auftrag als fehlgeschlagen markiert. Starte ihn
  dann neu.
- Fehlermeldungen beim Einhängen erscheinen als Fenster, zum Beispiel „Mount fehlgeschlagen: …“,
  „Unmount fehlgeschlagen: …“ oder „Remount fehlgeschlagen: …“.
- Findet das Diagnose-Log keine Meldungen des Archivers, zeigt es stattdessen die letzten allgemeinen Meldungen von
  HydraHive.

*Stand: Archiver 2.0.7, 22.11.2026*
