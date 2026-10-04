// Reine Logik für die Rechner-Liste — ohne App-Importe, damit sie in Tests läuft.
import type { GpuCard, Rig } from "./api"

export type RigBadge = "pending" | "online" | "offline" | "disabled" | "revoked"

/** Der Rig meldet alle 30 s; nach 2 min ohne Meldung gilt er als offline. */
export const OFFLINE_AFTER_MS = 120_000

export function rigBadge(rig: Pick<Rig, "status" | "enabled" | "last_seen">, now: number = Date.now()): RigBadge {
  if (rig.status === "revoked") return "revoked"
  if (rig.status === "pending") return "pending"
  if (!rig.enabled) return "disabled"
  const seen = rig.last_seen ? Date.parse(rig.last_seen) : Number.NaN
  return !Number.isNaN(seen) && now - seen <= OFFLINE_AFTER_MS ? "online" : "offline"
}

export const BADGE_CLASS: Record<RigBadge, string> = {
  pending: "bg-amber-500/20 text-amber-300",
  online: "bg-emerald-500/20 text-emerald-300",
  offline: "bg-rose-500/20 text-rose-300",
  disabled: "bg-zinc-700/60 text-zinc-300",
  revoked: "bg-zinc-800 text-zinc-500",
}

/** Gültige Rig-Namen wie im Backend (pairing.NAME_RE): auch Kryptex-Worker-Name. */
export function isValidRigName(name: string): boolean {
  return /^[a-z0-9][a-z0-9-]{0,31}$/.test(name)
}

export type Activity =
  | { kind: "mining"; coin: string; miner: string }
  | { kind: "benchmark"; coin: string; miner: string; done: number; total: number }
  | { kind: "stopped"; reason: string }

/** Was macht der Rechner gerade? ``total`` = Anzahl Coin×Miner-Paare für seinen Hersteller. */
export function activity(rig: Pick<Rig, "assignment" | "bench_done" | "bench_failed">, total: number): Activity {
  const a = rig.assignment
  if (!a || a.mode === "stop" || !a.coin || !a.miner) return { kind: "stopped", reason: a?.reason ?? "" }
  if (a.mode === "benchmark") {
    return { kind: "benchmark", coin: a.coin, miner: a.miner, done: rig.bench_done + rig.bench_failed + 1, total }
  }
  return { kind: "mining", coin: a.coin, miner: a.miner }
}

export interface ActivityLine { vendor: string | null; activity: Activity; hashrate: number | null | undefined }

type LineRig = Pick<Rig, "assignment" | "bench_done" | "bench_failed" | "bench_total" | "groups"> & {
  last_report: { hashrate?: number | null } | null
}

/** Eine Zeile je Hersteller-Gruppe; Rechner mit einem Hersteller (oder alter Server): eine Zeile ohne Etikett. */
export function activityLines(rig: LineRig): ActivityLine[] {
  const groups = rig.groups ?? []
  if (groups.length > 1) {
    return groups.map((g) => ({ vendor: g.vendor, activity: activity(g, g.bench_total), hashrate: g.hashrate }))
  }
  return [{ vendor: null, activity: activity(rig, rig.bench_total), hashrate: rig.last_report?.hashrate }]
}

/** Gründe des Servers → Übersetzungsschlüssel (unbekannte → generisch). */
const STOP_KEYS = ["awaiting_approval", "disabled", "no_kryptex_user", "no_supported_gpu", "power_budget",
  "power_source_down", "no_profitable_option", "mixed_rig_old_client", "amd_opencl_missing"] as const

export function stopReasonKey(reason: string): string {
  return (STOP_KEYS as readonly string[]).includes(reason) ? `stop_${reason}` : "stop_other"
}

/** Kryptex-Benutzername mit „.worker“-Teil? (häufiger Fehler: „krxABC.Mining“) */
export function userHasWorkerSuffix(user: string): boolean {
  return /^krx[A-Za-z0-9]+[./].+/.test(user.trim())
}

/** Karten eines Rigs für die Anzeige; ältere Clients (≤ 0.3.0) melden keine Einzelkarten. */
export function rigCards(rig: Pick<Rig, "last_report">): GpuCard[] {
  return rig.last_report?.gpus ?? []
}

/** Hinweis, warum Temperatur/Watt fehlen — oder null, wenn alles da ist. */
export function sensorHint(cards: GpuCard[]): "asleep" | "no_hwmon" | null {
  if (cards.some((c) => c.sensors === "no_hwmon")) return "no_hwmon"
  if (cards.some((c) => c.sensors === "asleep")) return "asleep"
  return null
}
