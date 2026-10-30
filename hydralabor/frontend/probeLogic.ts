/** Hydra-Labor L3: Probe-HydraHive im Labor – Typen und reine Hilfen. */
export interface ProbeState { built: boolean; running: boolean; user: string; password: string; port: number; open: boolean }

/** Aufträge der Probe (backend/jobs.py JOBS). */
export const PROBE_JOBS = ["probe_build", "probe_start", "probe_stop"]

/** Was der Kasten zeigt. Läuft die Probe ohne Durchreiche (halb gestartet), gilt sie als aus: „Starten“ richtet
 * beides neu ein. */
export function probeView(p: ProbeState, job: string): "busy" | "unbuilt" | "stopped" | "open" {
  if (PROBE_JOBS.includes(job)) return "busy"
  if (!p.built) return "unbuilt"
  return p.running && p.open ? "open" : "stopped"
}
