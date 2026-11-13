/** Reine Logik des Bereichs „Bauumgebung“ (ohne React), damit sie einzeln testbar ist. */
import type { ContainerState, TvwJob } from "./api"

/** Reihenfolge der Schritte, wie das Backend sie meldet. */
export const SETUP_STEPS = ["network", "container", "user", "packages", "tools", "sdk", "keystore", "probe", "stop"] as const

export type SetupView = "running" | "failed" | "ready" | "new"

/** Was der Bereich zeigt: läuft gerade, gescheitert, eingerichtet oder noch nie eingerichtet. */
export function setupView(job: TvwJob | null, container: ContainerState): SetupView {
  if (job?.state === "running") return "running"
  if (job?.state === "failed") return "failed"
  if (job?.state === "done" && container !== "missing") return "ready"
  return "new"
}

/** Fortschritt als „Schritt n von m“ (unbekannter Schritt → 0). */
export function stepIndex(step: string): { n: number; total: number } {
  const i = (SETUP_STEPS as readonly string[]).indexOf(step)
  return { n: i < 0 ? 0 : i + 1, total: SETUP_STEPS.length }
}

/** Während eines Auftrags (Einrichten oder Prüfen eines Fernsehers) öfter nachsehen, sonst gar nicht. */
export function pollMs(view: SetupView, deviceBusy = false): number | null {
  return view === "running" || deviceBusy ? 2000 : null
}
