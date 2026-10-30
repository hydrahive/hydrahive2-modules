/** Hydra-Labor: Typen und reine Hilfen – ohne React, gut zu testen. */
export const BASE = "/modules/hydralabor"

export interface LastTest { ok?: boolean; passed?: number; failed?: number; summary?: string; failures?: string[]; at?: string }
export interface LabState {
  step: "start" | "ready"; running: string; progress: string; error_code: string; error_step: string; model: string
  cpu: number; ram_mb: number; disk_gb: number; last_net_ok: string; last_test: LastTest; project_id: string
  agent_id: string; container_running: boolean; submit_out?: Record<string, unknown>
}
export interface Check { id: string; ok: boolean; code: string; have: number | string | null; need: number | string | null }
export interface Checks { ok: boolean; checks: Check[] }
export interface Limits { cpu: number; ram_mb: number; disk_gb: number }
export interface Model { id: string; label: string; provider: string }

/** Reihenfolge der Meldungen beim Anlegen (backend/jobs.py create + provision.STEPS). */
export const CREATE_STEPS = ["network", "container", "user", "packages", "node", "code", "python", "frontend", "links",
  "snapshot", "project"]

const ERR = new Set(["labor_busy", "labor_not_ready", "labor_already_ready", "labor_confirm_missing", "labor_interrupted",
  "labor_failed", "labor_net_open", "labor_dns_failed", "labor_net_probe_failed", "labor_network_missing",
  "labor_incus_failed", "labor_subnet_unavailable", "labor_launch_failed", "labor_limits_invalid", "labor_no_address",
  "labor_no_storage_pool", "labor_setup_failed", "labor_snapshot_failed", "labor_no_snapshot", "labor_reset_failed",
  "labor_project_failed", "labor_model_unavailable", "labor_incus_missing", "labor_incus_too_old", "labor_storage_low",
  "labor_memory_low", "labor_core_too_old", "admin_only",
  "labor_github_denied", "labor_github_expired", "labor_github_failed", "labor_github_fork_failed",
  "labor_github_name_taken", "labor_github_not_configured", "labor_github_not_connected", "labor_github_not_started",
  "labor_github_rate_limited", "labor_github_scope", "labor_github_unreachable", "labor_github_url",
  "labor_report_failed", "labor_submit_bundle_invalid", "labor_submit_git_failed", "labor_submit_nothing",
  "labor_submit_pr_failed", "labor_submit_protected", "labor_submit_push_failed", "labor_submit_secret",
  "labor_submit_target_invalid", "labor_submit_tests_red", "labor_submit_text_invalid", "labor_submit_too_big"])

/** Text-Schlüssel zu einem Fehler aus einer Antwort ({code}) oder direkt einem Code aus dem Zustand. */
export function errorKey(e: unknown): string {
  const code = typeof e === "string" ? e : typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  return typeof code === "string" && ERR.has(code) ? `err.${code}` : "err.general"
}

export function progressOf(s: LabState): { index: number; pct: number } {
  if (s.running !== "create") return { index: -1, pct: 0 }
  const i = Math.max(0, CREATE_STEPS.indexOf(s.progress))
  return { index: i, pct: Math.round((i / CREATE_STEPS.length) * 100) }
}

const between = (v: number, lo: number, hi: number) => Number.isInteger(v) && v >= lo && v <= hi

/** Wie backend/container.py Limits. */
export function limitsError(l: Limits): string {
  return between(l.cpu, 1, 64) && between(l.ram_mb, 1024, 262144) && between(l.disk_gb, 10, 2000)
    ? "" : "err.labor_limits_invalid"
}

export function testLine(t: LastTest): { key: string; passed: number; failed: number } | null {
  if (!t.at) return null
  const passed = t.passed ?? 0, failed = t.failed ?? 0
  if (t.ok) return { key: "test.green", passed, failed }
  return { key: t.summary ? "test.red" : "test.broken", passed, failed }
}

export function when(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString()
}

/** „Labor entfernen“ nur mit genau diesem Wort (wie backend/routes.py). */
export const canRemove = (w: string) => w === "LABOR"

/** Welche Ansicht die Seite zeigt: während des Entfernens nur einen Hinweis (sonst sähe es nach „neu anlegen“ aus). */
export function viewFor(s: LabState): "busy" | "lab" | "wizard" {
  if (s.running === "remove") return "busy"
  return s.step === "ready" ? "lab" : "wizard"
}
