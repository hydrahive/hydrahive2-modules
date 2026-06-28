import type { HAState } from "./api"

// Domains, die sich per turn_on/turn_off/toggle schalten lassen.
const TOGGLEABLE = new Set([
  "light", "switch", "fan", "input_boolean", "automation", "script", "siren",
])

export function isToggleable(s: HAState): boolean {
  return TOGGLEABLE.has(s.domain)
}

export function isOn(s: HAState): boolean {
  return s.state === "on" || s.state === "open" || s.state === "playing"
}

// Liefert {domain, service} für ein Toggle des aktuellen Zustands.
export function toggleCall(s: HAState): { domain: string; service: string } {
  return { domain: s.domain, service: isOn(s) ? "turn_off" : "turn_on" }
}

// Lesbarer Zustandstext inkl. Einheit (z.B. "21.5 °C", "an", "aus").
export function displayState(s: HAState): string {
  if (s.unit) return `${s.state} ${s.unit}`
  const map: Record<string, string> = {
    on: "an", off: "aus", open: "offen", closed: "zu",
    unavailable: "nicht verfügbar", unknown: "unbekannt",
  }
  return map[s.state] ?? s.state
}

// Domain-Metadaten: deutsches Label, lucide-Icon-Name, Sortier-Priorität.
// Niedrigere Priorität = weiter oben. Steuerbares zuerst, Sensorik danach,
// technische Helfer ganz unten.
interface DomainMeta {
  label: string
  icon: string
  prio: number
}

const DOMAIN_META: Record<string, DomainMeta> = {
  light: { label: "Lampen", icon: "Lightbulb", prio: 1 },
  switch: { label: "Schalter", icon: "ToggleLeft", prio: 2 },
  climate: { label: "Heizung & Klima", icon: "Thermometer", prio: 3 },
  cover: { label: "Rollos & Türen", icon: "Blinds", prio: 4 },
  fan: { label: "Ventilatoren", icon: "Fan", prio: 5 },
  media_player: { label: "Medien", icon: "Speaker", prio: 6 },
  vacuum: { label: "Staubsauger", icon: "Bot", prio: 7 },
  lock: { label: "Schlösser", icon: "Lock", prio: 8 },
  scene: { label: "Szenen", icon: "Clapperboard", prio: 9 },
  script: { label: "Skripte", icon: "ScrollText", prio: 10 },
  automation: { label: "Automationen", icon: "Workflow", prio: 11 },
  sensor: { label: "Sensoren", icon: "Gauge", prio: 12 },
  binary_sensor: { label: "Kontakte & Melder", icon: "RadioTower", prio: 13 },
  input_boolean: { label: "Schalter (virtuell)", icon: "ToggleLeft", prio: 14 },
  person: { label: "Personen", icon: "User", prio: 15 },
  device_tracker: { label: "Geräte-Tracker", icon: "MapPin", prio: 16 },
  weather: { label: "Wetter", icon: "CloudSun", prio: 17 },
  sun: { label: "Sonne", icon: "Sun", prio: 18 },
  update: { label: "Updates", icon: "Download", prio: 19 },
  button: { label: "Buttons", icon: "Circle", prio: 20 },
  number: { label: "Werte", icon: "Hash", prio: 21 },
  select: { label: "Auswahl", icon: "List", prio: 22 },
}

export function domainLabel(domain: string): string {
  return DOMAIN_META[domain]?.label ?? domain
}

export function domainIcon(domain: string): string {
  return DOMAIN_META[domain]?.icon ?? "Box"
}

function domainPrio(domain: string): number {
  return DOMAIN_META[domain]?.prio ?? 99
}

// Domains nach sinnvoller Priorität sortiert (steuerbar zuerst).
export function sortDomains(domains: string[]): string[] {
  return [...domains].sort((a, b) => {
    const pa = domainPrio(a)
    const pb = domainPrio(b)
    return pa !== pb ? pa - pb : a.localeCompare(b)
  })
}

// Gruppiert States nach Domain, nach Priorität sortiert (Lampen/Schalter oben).
export function groupByDomain(states: HAState[]): [string, HAState[]][] {
  const groups = new Map<string, HAState[]>()
  for (const s of states) {
    const arr = groups.get(s.domain) ?? []
    arr.push(s)
    groups.set(s.domain, arr)
  }
  return [...groups.entries()]
    .map(([d, arr]) => [d, arr.sort((a, b) => a.name.localeCompare(b.name))] as [string, HAState[]])
    .sort((a, b) => {
      const pa = domainPrio(a[0])
      const pb = domainPrio(b[0])
      return pa !== pb ? pa - pb : a[0].localeCompare(b[0])
    })
}
