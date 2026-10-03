// Reine Logik für die Rechner-Liste — ohne App-Importe, damit sie in Tests läuft.
import type { Rig } from "./api"

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
