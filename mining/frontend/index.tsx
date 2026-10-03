import { MiningPage } from "./MiningPage"

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
    },
  },
}
