# TV-Werkstatt: Aufspielen auf Google TV (0.8.0)

Anlass: TCL 98" „Smart TV Pro“ (G08, MT9689, Google TV 14, Firmware `UTT2.250416.001 AU02`), Original-Startbildschirm
`com.google.android.apps.tv.launcherx`. Der Ablauf aus E1 kannte nur den Sony (Android TV 9).

## Problem

Auf Google TV beansprucht neben dem Original auch Googles Einrichtungs-Helfer Home:
`com.google.android.tungsten.setupwraith/.RecoveryActivity` (am TCL gelesen, 13.11.2026). Wird das Original
abgeschaltet, verwirft Android die Home-Wahl, und der Helfer kann Home übernehmen und das System in eine Schleife bringen
(cleanyourtv `launcher/build-and-install.sh`, b953804). Gehört dem Helfer das gespeicherte WLAN, löscht Android es beim
Abschalten (cleanyourtv `tools/disable.sh`).

## Ablauf (backend/guard.py, install_jobs.py)

1. **Vorprüfung, nur lesend:** wer Home beansprucht, wem gespeicherte WLANs gehören, ob überhaupt eines gespeichert ist,
   wer jetzt Home ist. Beansprucht der Helfer Home nicht (Sony) → nichts Zusätzliches.
2. Helfer beansprucht Home → nur weiter, wenn das Original jetzt Home ist und das WLAN nicht dem Helfer gehört
   (`tvw_wifi_owned_by_setup`) und die Besitzer lesbar sind (`tvw_wifi_unreadable`). Sonst: nichts geändert.
3. Erst **vermerken** (`extra_disabled`, Migration 005), dann den Helfer abschalten, solange das Original Home ist,
   zurücklesen (Home muss beim Original bleiben, sonst `tvw_guard_failed` + Rückweg).
4. Weiter wie bisher: aufspielen, neuen Startbildschirm starten, Original abschalten, Home setzen, zurücklesen.
5. **Jeder** Fehler nach Schritt 3 → automatisch zurück: Original und Helfer einschalten, dann Original als Home.
   Scheitert auch das → `tvw_restore_incomplete`, der Vermerk bleibt, damit „Zurück zum Original“ es nachholt.
6. „Zurück zum Original“ schaltet Original und Vermerktes ein; der Vermerk fällt erst, wenn Home wieder das Original ist.

Nur abschalten, nie deinstallieren. Abgeschaltet wird nur, was die Vorprüfung selbst vorschlägt (feste Liste).

## Bewusst nicht drin (Variante A, Entscheidung Till 13.11.2026)

Kein Tastenhelfer. Folge am TCL laut Profil `tcl-55q7d-pro-google-tv` (gleiche Fernbedienung `BT_RC833A_B5`, gleiche
Firmware): YouTube (190) und TV-Symbol (4001) tun nichts, Einstellungen (83) nur auf dem Startbildschirm; Netflix,
Prime, Disney+, TCL Channels, Eingang und Lautstärke-Halten gehen. Die Rückfrage sagt das vor dem Aufspielen.
Später prüfbar: Tastenhelfer mit `consume_volume_keys` gegen das verlorene Lautstärke-Halten (für AU02 nicht berichtet).
