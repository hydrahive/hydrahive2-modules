import { MiningPage } from "./MiningPage"
import { runtimeDe, runtimeEn } from "./i18nRuntime"

export const routes = [{ path: "/mining", element: <MiningPage /> }]

export const nav = [
  {
    path: "/mining",
    icon: "Pickaxe",
    labelKey: "mining",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

const rigsDe = {
  rigs_title: "Rechner", rigs_empty: "Noch kein Rechner gekoppelt. „Rechner koppeln“ erzeugt einen Befehl für den Rechner.",
  earnings_title: "Erträge je Coin",
  pair_button: "Rechner koppeln", pair_title: "Neuen Rechner koppeln", rig_name: "Name des Rechners",
  rig_name_hint: "Nur Kleinbuchstaben, Ziffern und Bindestrich, höchstens 32 Zeichen. Der Name erscheint auch bei Kryptex.",
  pair_create: "Befehl erzeugen", cancel: "Abbrechen", done: "Fertig", copy: "Kopieren", copied: "Kopiert.",
  pair_step1: "1. Diesen Befehl auf dem Rechner „{{name}}“ in ein Terminal einfügen:",
  pair_step2: "2. Danach erscheint der Rechner unten als „wartet auf Freigabe“. Dort auf „Freigeben“ klicken.",
  pair_code: "Code", pair_valid_until: "gültig bis {{time}}, nur einmal verwendbar",
  pair_pinned: "Server-Zertifikat ist im Befehl hinterlegt",
  col_rig: "Rechner", col_state: "Zustand", col_temp: "Temp.", col_power: "Strom", col_load: "Last", col_system: "System",
  badge_pending: "wartet auf Freigabe", badge_online: "online", badge_offline: "offline",
  badge_disabled: "ausgeschaltet", badge_revoked: "gesperrt",
  approve: "Freigeben", turn_off: "Ausschalten", turn_on: "Einschalten", revoke: "Sperren", remove: "Entfernen",
  revoke_confirm: "Rechner sperren? Er verliert sofort den Zugang und muss neu gekoppelt werden.",
}
const rigsEn = {
  rigs_title: "Rigs", rigs_empty: "No rig paired yet. “Pair rig” creates a command for the machine.",
  earnings_title: "Earnings per coin",
  pair_button: "Pair rig", pair_title: "Pair a new rig", rig_name: "Rig name",
  rig_name_hint: "Lowercase letters, digits and hyphen only, max. 32 characters. The name is also shown on Kryptex.",
  pair_create: "Create command", cancel: "Cancel", done: "Done", copy: "Copy", copied: "Copied.",
  pair_step1: "1. Paste this command into a terminal on “{{name}}”:",
  pair_step2: "2. The rig then appears below as “awaiting approval”. Click “Approve” there.",
  pair_code: "Code", pair_valid_until: "valid until {{time}}, single use",
  pair_pinned: "server certificate is pinned in the command",
  col_rig: "Rig", col_state: "State", col_temp: "Temp.", col_power: "Power", col_load: "Load", col_system: "System",
  badge_pending: "awaiting approval", badge_online: "online", badge_offline: "offline",
  badge_disabled: "switched off", badge_revoked: "revoked",
  approve: "Approve", turn_off: "Switch off", turn_on: "Switch on", revoke: "Revoke", remove: "Remove",
  revoke_confirm: "Revoke this rig? It loses access immediately and has to be paired again.",
}

const regionsDe = {
  region_global: "Weltweit", region_eu: "Europa", region_us: "Nordamerika", region_br: "Südamerika",
  region_sg: "Singapur", region_hk: "Hongkong", region_ru: "Russland", region_ae: "Naher Osten",
}
const regionsEn = {
  region_global: "Global", region_eu: "Europe", region_us: "North America", region_br: "South America",
  region_sg: "Singapore", region_hk: "Hong Kong", region_ru: "Russia", region_ae: "Middle East",
}

export const i18n = {
  de: {
    mining: {
      title: "Mining",
      subtitle: "Was bringt welcher Coin gerade bei Kryptex?",
      refresh: "Jetzt abrufen",
      gpu: "Grafikkarte",
      never_fetched: "Noch keine Daten von Kryptex",
      fresh: "Stand: vor {{min}} min",
      stale: "Veraltet: Stand vor {{min}} min. Kryptex ist gerade nicht erreichbar",
      empty: "Noch keine Coins geladen. Der erste Abruf läuft kurz nach dem Start.",
      col_coin: "Coin", col_algo: "Algorithmus", col_hashrate: "Hashrate", col_fee: "Gebühr",
      col_day: "pro Tag", col_month: "pro Monat",
      best: "bester",
      prop_hint: "PROP: Auszahlung schwankt mit dem Glück des Pools",
      estimated_hint: "Selbst gerechnet aus Ausschüttung und Netz-Hashrate (Kryptex liefert hier keinen Wert)",
      reference_note: "Hashraten: Kryptex-Angaben für die Karte (Stand {{date}}), ohne Übertakten. Echte Werte misst später jeder Rechner selbst.",
      estimated_note: "* = selbst gerechnet.",
      settings: "Einstellungen",
      kryptex_user: "Kryptex-Benutzername (oder Wallet)",
      kryptex_user_ph: "z. B. dein Kryptex-Login",
      region: "Server-Region",
      switch_threshold: "Wechseln ab mehr Ertrag (%)",
      min_runtime: "Frühestens wechseln nach (Minuten)",
      prop_discount: "Abschlag für PROP-Coins (%)",
      save: "Speichern",
      ...regionsDe,
      ...rigsDe,
      ...runtimeDe,
    },
  },
  en: {
    mining: {
      title: "Mining",
      subtitle: "What does each coin earn on Kryptex right now?",
      refresh: "Fetch now",
      gpu: "Graphics card",
      never_fetched: "No data from Kryptex yet",
      fresh: "Updated {{min}} min ago",
      stale: "Outdated: last update {{min}} min ago. Kryptex is currently unreachable",
      empty: "No coins loaded yet. The first fetch runs shortly after startup.",
      col_coin: "Coin", col_algo: "Algorithm", col_hashrate: "Hashrate", col_fee: "Fee",
      col_day: "per day", col_month: "per month",
      best: "best",
      prop_hint: "PROP: payout varies with the pool's luck",
      estimated_hint: "Calculated from emission and network hashrate (Kryptex provides no value here)",
      reference_note: "Hashrates: Kryptex figures for this card (as of {{date}}), stock clocks. Each rig will measure real values later.",
      estimated_note: "* = calculated.",
      settings: "Settings",
      kryptex_user: "Kryptex username (or wallet)",
      kryptex_user_ph: "e.g. your Kryptex login",
      region: "Server region",
      switch_threshold: "Switch at more earnings (%)",
      min_runtime: "Earliest switch after (minutes)",
      prop_discount: "Discount for PROP coins (%)",
      save: "Save",
      ...regionsEn,
      ...rigsEn,
      ...runtimeEn,
    },
  },
}
