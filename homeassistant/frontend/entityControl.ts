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

// Gruppiert States nach Domain, alphabetisch sortiert.
export function groupByDomain(states: HAState[]): [string, HAState[]][] {
  const groups = new Map<string, HAState[]>()
  for (const s of states) {
    const arr = groups.get(s.domain) ?? []
    arr.push(s)
    groups.set(s.domain, arr)
  }
  return [...groups.entries()]
    .map(([d, arr]) => [d, arr.sort((a, b) => a.name.localeCompare(b.name))] as [string, HAState[]])
    .sort((a, b) => a[0].localeCompare(b[0]))
}
