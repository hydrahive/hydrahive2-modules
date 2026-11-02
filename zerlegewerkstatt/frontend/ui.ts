// Gemeinsame Bausteine der Zerlege-Werkstatt.
// Farben kommen aus den Farbstufen des Kerns, keine eigenen Hex-Werte.
import type { AnalysisType, Artifact, Purpose } from "./api"

export const BOX = "bg-[rgb(var(--hh-s-box,21_28_43))]"
export const RAND = "border-[rgb(var(--hh-s-rand,42_54_75))]"
export const TEXT = "text-[#e8eef8]"
export const MUTED = "text-[#9aa7bc]"

export const panel = `rounded-xl border ${RAND} ${BOX} p-4`
export const button = `rounded-lg bg-[rgb(var(--hh-s-hebung,27_37_54))] px-4 py-2 text-sm ${TEXT} hover:bg-[rgb(var(--hh-s-rand-hover,70_97_127))] disabled:opacity-40 transition-colors`
export const input = `rounded-lg border ${RAND} ${BOX} px-3 py-2 text-sm ${TEXT} placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]`
export const label = `block text-xs ${MUTED} mb-1`

export const ANALYSIS_TYPES: { id: AnalysisType; kinds: string[] }[] = [
  { id: "inspect-artifact", kinds: ["pe", "apk", "elf", "pcap", "pcapng", "firmware"] },
  { id: "inspect-android-package", kinds: ["apk"] },
  { id: "inspect-managed-artifact", kinds: ["pe"] },
  { id: "analyze-ghidra", kinds: ["pe", "elf", "firmware"] },
]

export const PURPOSES: { id: Purpose; label: string }[] = [
  { id: "interoperability", label: "Interoperabilität mit dem eigenen Gerät" },
  { id: "security_audit", label: "Sicherheitsprüfung des eigenen Geräts" },
  { id: "debugging", label: "Fehlersuche an eigener Software" },
  { id: "preservation", label: "Sicherung eigener Funktionalität" },
  { id: "other_authorized", label: "Sonstige erlaubte Untersuchung" },
]

export function analysisFor(kind: string): AnalysisType[] {
  return ANALYSIS_TYPES.filter((entry) => entry.kinds.includes(kind)).map((entry) => entry.id)
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`
  return `${(size / (1024 * 1024)).toFixed(1)} MiB`
}

export function artifactIcon(kind: string): string {
  if (kind === "apk") return "Smartphone"
  if (kind === "pcap" || kind === "pcapng") return "Network"
  if (kind === "firmware") return "Cpu"
  return "FileCode"
}

export function artifactLabel(artifact: Artifact): string {
  return `${artifact.original_name} · ${artifact.kind} · ${formatBytes(artifact.size_bytes)}`
}
