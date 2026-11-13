# TV-Werkstatt E3: Zusätze

Zielbild: Reiter „Zusätze“ der Klick-Demo (`generated/tv-werkstatt/demo.html`): Katalog mit Filtern, Rechte vor der
Installation, Bauen & installieren, Entfernen, Stand je Fernseher. Teil 1 (0.12.0) = Katalog aus cleanyourtv.
Teil 2 (später) = eigener Zusatz per GitHub-Adresse.

## Teil 1 – Katalog aus cleanyourtv (0.12.0)

- **Katalog laden** (Auftrag `addon_catalog`, nur lesend): aus der Quelle am festen Stand (b953804) nur
  `addons/README.md`, `*/app/build.gradle*`, `*/app/src/main/AndroidManifest.xml`, `*/screenshot.jpg` als tar; auf dem
  Server nur im Speicher gelesen (Text ≤ 200 KB, Bild ≤ 2 MB, gesamt ≤ 15 MB). Grundlage ist jeder Ordner mit
  `app/build.gradle*`, die README-Tabelle liefert Name, Beschreibung, Autor, „getestet auf“. Bilder auf 640×360 JPEG.
  Ablage je Stand unter `data_dir/tvwerkstatt/addons/<commit>/`.
- **Rechte:** im Katalog aus `<uses-permission>` des Manifests; nach dem Bau die der fertigen App (`aapt2 dump
  permissions`, inkl. Bibliotheken). Rot: `WRITE_SECURE_SETTINGS`, `REQUEST_INSTALL_PACKAGES`, `UPDATE_PACKAGES_…`,
  `DUMP`; gelb: Einblenden, Autostart, Hintergrund, Nutzungsdaten, Standort, genaue Wecker, Bedienungshilfe.
- **Bauen & installieren** (Auftrag `addon_install`, Rückfrage nennt die Rechte): Quelle → Bauwerkzeug prüfen (Gradle-
  Wrapper eigener oder `../../launcher`, Jar und Distribution gegen gradle.org: 8.9 und 8.11.1) → `./gradlew
  assembleRelease` → Auswertung (erwartetes Paket, Version, minSdk, Rechte) → `pm install -r`. **Installationsskripte
  der Zusätze laufen nicht, die Werkstatt vergibt keine Sonderrechte** (kein `pm grant`, `appops`, `settings put`).
  minSdk wird vor dem Start gegen den Fernseher geprüft.
- **Entfernen** (`addon_remove`): nur wenn der Fernseher das Paket als nachinstalliert führt, danach zurücklesen.

Gemessen 13.11.2026 (echt): Katalog 36 Zusätze, 36 Bilder, tar 2,8 MB in 0,1 s; Bauwerkzeug-Prüfung 36/36 ok (nach Fund:
tv-hub nutzt den 8.9-Wrapper-Jar mit 8.11.1-Distribution – Jar wird jetzt versionsunabhängig gegen beide Prüfsummen
geprüft). Bau koi-pond 9 s / 4 s (zweiter Lauf), tv-inspector 8 s, weather 8 s (Rechte INTERNET). Sony: koi-pond
installiert in 2,2 s, als Bildschirmschoner `.PondDream` gemeldet, wieder entfernt; Paketliste, Bildschirmschoner und Home
vorher = nachher.

## Was ein Zusatz danach braucht

Einige Zusätze erwarten nach der Installation Handgriffe, die bei cleanyourtv das Skript macht (Bildschirmschoner
wählen, `WRITE_SECURE_SETTINGS` für „Remote Access“, Einblenden über Apps, Bedienungshilfe). Die Werkstatt macht das
bewusst nicht ungefragt; die Beschreibung im Katalog nennt es. Ein eigener Schritt „Bildschirmschoner setzen“ ist ein
Kandidat für später.
