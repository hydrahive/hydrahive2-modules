// Ghostwriter G2 – Lauf-Anzeige ohne React (runView.test.ts): zählen, Ende erkennen, Nachladen bestimmen.

export type RunStatus = "queued" | "running" | "done" | "cancelled" | "limit" | "error"
export type SceneRunState = "waiting" | "writing" | "written" | "proposal" | "skipped_filled" | "skipped_no_summary" | "error"

export interface RunInfo {
  id: string; status: RunStatus; scope: string; model: string; current_scene: string | null
  tokens_in: number; tokens_out: number; cost_micros: number | null; cost_partial: boolean; error: string | null
  options: Record<string, unknown>
  progress: { scene_id: string; state: SceneRunState; words?: number }[]
}

export function isFinished(run: RunInfo | null): boolean {
  return !run || !(run.status === "queued" || run.status === "running")
}

export function progressCounts(run: RunInfo) {
  const c = { total: run.progress.length, written: 0, proposals: 0, skipped: 0, errors: 0, open: 0, words: 0 }
  for (const p of run.progress) {
    if (p.state === "written") c.written += 1
    else if (p.state === "proposal") c.proposals += 1
    else if (p.state === "skipped_filled" || p.state === "skipped_no_summary") c.skipped += 1
    else if (p.state === "error") c.errors += 1
    else c.open += 1
    c.words += p.words ?? 0
  }
  return c
}

/** Welche Szenen seit dem vorigen Stand fertig wurden: direkt geschrieben (Szene neu laden) oder als
 *  Vorschlag abgelegt (Hinweis an der Szene zeigen). */
export function scenesToReload(before: RunInfo | null, after: RunInfo) {
  const was = new Map((before?.progress ?? []).map((p) => [p.scene_id, p.state]))
  const written: string[] = []
  const proposals: string[] = []
  for (const p of after.progress) {
    if (was.get(p.scene_id) === p.state) continue
    if (p.state === "written") written.push(p.scene_id)
    if (p.state === "proposal") proposals.push(p.scene_id)
  }
  return { written, proposals }
}

/** Mikro-Cent → Cent mit zwei Stellen. Unbekannter Tarif → null (keine Euro-Angabe). */
export function costLabel(micros: number | null, partial: boolean): { cents: string; partial: boolean } | null {
  if (micros === null) return null
  return { cents: (micros / 1000).toFixed(2), partial }
}
