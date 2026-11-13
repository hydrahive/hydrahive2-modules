# TV-Werkstatt: Reiter „Apps“ (App-Verwaltung mit dem Play Store, 0.11.0)

Wunsch Till 13.11.2026: „die app verwaltung mit einbauen das ich den appstore des tv's benutzen kann“. Nicht Teil der
Klick-Demo; neuer Reiter zwischen „Entrümpeln“ und „Zusätze“.

## Was es kann

- **Selbst installierte Apps lesen** (`pm list packages -3`): Paket, Version, Herkunft (`installerPackageName`), an/aus.
  Name aus „Apps vom Fernseher lesen“ (Desktop), sonst Paketname. Nur lesend.
- **Play Store am Fernseher öffnen:** bei einer App (`market://details?id=…`) oder mit einer Suche
  (`market://search?q=…`), fest an `com.android.vending`. Suchtext: Buchstaben, Ziffern, Leerzeichen, `. , & ' + -`,
  1–60 Zeichen, keine Steuerzeichen, URL-kodiert. **Installieren bestätigt man am Fernseher** – stilles Installieren aus
  dem Store lässt Google nicht zu.
- **Deinstallieren** mit Rückfrage: nur Apps, die der Fernseher selbst als nachinstalliert führt (Prüfung im Skript auf
  dem Gerät, erst dann `pm uninstall`, danach zurücklesen). Nie der Startbildschirm der Werkstatt, das Original, der
  Play Store oder Android selbst. Vorinstalliertes bleibt Sache von „Entrümpeln“ (nur abschalten).

## Gemessen 13.11.2026

- Lesen: Sony 7 Apps in 1,2 s, TCL 9 Apps in 2,0 s; alle mit Version, Herkunft Play Store außer dem Startbildschirm.
- Sony (Testgerät): „Im Store öffnen“ (Emby) und „Suchen“ („Kodi Media Center“) → Fokus `com.android.vending`, danach Home
  → wieder der Startbildschirm. Beim zweiten Aufruf meldet Android „delivered to currently running top-most instance“ –
  gilt als Erfolg.
- Sony: Deinstallieren einer vorinstallierten App (`com.sony.dtv.imanual`) lehnt das Gerät selbst ab
  (`tvw_store_not_user_app`), `pm uninstall` läuft nicht, Paketliste vorher = nachher.
- Am TCL nur gelesen; Öffnen/Suchen dort nicht geprüft.
