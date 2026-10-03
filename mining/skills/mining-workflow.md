---
name: mining-workflow
description: Mining-Modul auswerten und verwalten — Zustand der Rechner, Erträge, Verlauf, Messungen, Rechner schalten, Einstellungen, Fehlersuche
when_to_use: Wenn der User nach Mining, Rechnern/Rigs, Grafikkarten, Hashrate, Kryptex, Ertrag/Verdienst, Benchmark, Energie-/PV-Steuerung fragt oder einen Rechner ein-/ausschalten will
tools_required: [mining_status, mining_earnings, mining_rig_history, mining_benchmarks, mining_rig_control, mining_settings]
---

# Mining mit HydraHive

HydraHive verwaltet GPU-Rechner („Rigs“), die über Kryptex schürfen. Jeder Rechner
misst zuerst alle Coins, die seine Karte kann (Benchmark, je ca. 3 min), danach
schürft er den Coin mit dem höchsten Ertrag. Gewechselt wird nur, wenn ein anderer
Coin um mehr als die Schwelle besser ist **und** die Mindestlaufzeit um ist.

## Werkzeuge

| Frage / Auftrag | Werkzeug |
|---|---|
| „Wie läuft das Mining?“, „Welche Rechner sind offline?“ | `mining_status` |
| „Was verdiene ich?“, „Ertrag der letzten Woche?“ | `mining_earnings` (hours: 24 oder 168) |
| „Warum ist rig-03 so schwach?“, „Was hat rig-01 heute gemacht?“ | `mining_rig_history` |
| „Welcher Coin lohnt auf rig-02?“, „Was ist beim Messen schiefgegangen?“ | `mining_benchmarks` |
| „Schalte rig-04 aus“, „Miss rig-02 neu“ | `mining_rig_control` |
| „Wechsle erst ab 10 % mehr Ertrag“, Energie-Steuerung | `mining_settings` |

Immer zuerst `mining_status`, wenn unklar ist, wie ein Rechner heißt.

## Regeln

- **Vor jedem Schalten oder Ändern kurz sagen, was passiert, und bei mehreren Rechnern
  oder Energie-Einstellungen nachfragen.** Ausschalten stoppt das Schürfen sofort.
- Wirkt erst beim nächsten Melden des Rechners (ca. 30 s) — das dem User sagen.
- Koppeln, Freigeben, Sperren, Löschen und den Kryptex-Benutzer ändern gehen **nur in
  der Oberfläche** (Mining-Seite). Nicht versuchen, das anders zu erreichen.
- Fehlt die Freigabe `mining.control`, kann Buddy nur lesen — dann auf den Admin verweisen.
- Erträge sind **Schätzungen** (Hashrate × Kryptex-Angabe × Kurs), keine Auszahlung.
  Kryptex zahlt gesammelt aus; Abweichungen von einigen Prozent sind normal (PROP-Coins
  schwanken mit dem Pool-Glück).

## Auswertung

- **Leistung %** = aktuelle Hashrate im Verhältnis zur eigenen Benchmark-Messung.
  Dauerhaft unter ~90 %: Karte zu heiß (Drosselung), Treiber-Problem oder Übertaktung
  geändert → `mining_rig_history` (Temperatur) prüfen, ggf. neu messen.
- **Temperatur** über ~80 °C bei NVIDIA bzw. ~90 °C Hotspot bei AMD: Lüftung/Staub prüfen.
- **Watt** zusammen mit Ertrag ergibt die Effizienz; bei PV-Betrieb zählt sie für die
  Reihenfolge, in der Rechner zugeschaltet werden.
- Rohe Hashraten verschiedener Coins nie direkt vergleichen (MH/s vs. kH/s vs. TH/s) —
  immer über €/Tag.

## Fehlersuche

| Zustand | Bedeutung | Vorgehen |
|---|---|---|
| offline | Server hat seit 2 min nichts gehört | Am Rechner: `sudo journalctl -u hydrahive-rig -n 40` |
| angehalten (no_kryptex_user) | Kryptex-Benutzer fehlt | In der Oberfläche eintragen (nur `krx…`, ohne „.Worker“) |
| angehalten (no_supported_gpu) | keine Karte erkannt | Treiber prüfen: NVIDIA `nvidia-smi`, AMD `ls /sys/class/drm/card*/device/hwmon` |
| angehalten (power_budget / power_source_down) | Energie-Steuerung hält an | Normal bei wenig PV; Quelle prüfen, wenn dauerhaft |
| Benchmark-Fehlschlag | Miner lief auf der Karte nicht (z. B. zu wenig Speicher) | `mining_benchmarks` zeigt den Fehler; nach Treiber-Update neu messen |
| „Sensoren schlafen“ (AMD) | Karte im Ruhezustand, Linux ≥ 6.15 liefert dann keine Werte | Unkritisch; Werte kommen beim Schürfen |
| error `fetch:…` | Miner-Download fehlgeschlagen | Internet am Rechner prüfen; versucht es erneut |
| error `watchdog:…` | Miner abgestürzt oder ohne Hashrate | Rechner nimmt nach 3 Versuchen einen anderen Coin; Miner-Log am Rechner: `sudo tail -30 /var/lib/hydrahive-rig/miner.log` |

Client am Rechner aktualisieren (Kopplung bleibt):
`curl -fsSL https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh | sudo sh -s -- --update`
