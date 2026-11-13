/** Reine Logik des Bereichs „Startbildschirm“ (ohne React). */
import type { TvwBuild, TvwJob } from "./api"

export const BUILD_STEPS = ["container", "fetch", "verify", "build", "collect"] as const

export type BuildView = "running" | "failed" | "done" | "none"

export function buildView(job: TvwJob | null | undefined, builds: TvwBuild[]): BuildView {
  if (job?.state === "running") return "running"
  if (job?.state === "failed") return "failed"
  return lastGood(builds) ? "done" : "none"
}

/** Neuester erfolgreicher Bau (die Liste kommt neueste zuerst). */
export function lastGood(builds: TvwBuild[]): TvwBuild | undefined {
  return builds.find((b) => b.state === "done" && b.part === "launcher")
}

/** „Schritt n von m“ für den Bau. */
export function buildStep(step: string): { n: number; total: number } {
  const i = (BUILD_STEPS as readonly string[]).indexOf(step)
  return { n: i < 0 ? 0 : i + 1, total: BUILD_STEPS.length }
}

/** Prüfsumme gekürzt zum Ansehen (vorn und hinten), volle Länge im Titel. */
export function shortHash(h?: string): string {
  return h && h.length > 16 ? `${h.slice(0, 8)}…${h.slice(-8)}` : h ?? ""
}

/** Größe in KB/MB, deutsch gerundet. */
export function sizeText(bytes?: number): string {
  if (!bytes) return ""
  return bytes >= 1_000_000 ? `${(bytes / 1_000_000).toFixed(1).replace(".", ",")} MB` : `${Math.round(bytes / 1000)} KB`
}
