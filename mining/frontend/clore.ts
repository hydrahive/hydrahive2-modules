// Clore-Probelauf: Typen und reine Anzeige-Helfer (testbar ohne React).

export interface CloreRun {
  ts: string
  ok: boolean
  free: number
  rated: number
  hits: number
  best_roi: number | null
  error?: string | null
}

export interface CloreHit {
  ts: string
  server_id: number
  gpu: string | null
  count: number
  coin: string
  source: "measured" | "reference"
  revenue: number
  cost_od: number | null
  cost_spot: number | null
  roi_od: number | null
  roi_spot: number | null
  reliability: number | null
  mrl: number | null
  seen: number
}

export interface CloreDay { day: string; runs: number; runs_with_hits: number; best_roi: number | null; top_gpu: string | null }

export interface CloreSummary { last_run: CloreRun | null; hits_24h: CloreHit[]; days: CloreDay[]; enabled: boolean }

/** „nvidia-rtx-3060-ti“, 2 → „2× RTX 3060 Ti“ */
export function gpuLabel(gpu: string | null, count: number): string {
  if (!gpu) return "—"
  const name = gpu.replace(/^(nvidia|amd)-/, "").split("-")
    .map((p) => (/^(rtx|gtx|rx)$/.test(p) ? p.toUpperCase() : p === "ti" ? "Ti" : p.toUpperCase()))
    .join(" ")
  return `${count}× ${name}`
}

export function bestRoi(h: Pick<CloreHit, "roi_od" | "roi_spot">): { roi: number | null; kind: "od" | "spot" | null } {
  const od = h.roi_od ?? null
  const spot = h.roi_spot ?? null
  if (od === null && spot === null) return { roi: null, kind: null }
  if (spot !== null && (od === null || spot > od)) return { roi: spot, kind: "spot" }
  return { roi: od, kind: "od" }
}

export function toEur(usd: number | null | undefined, usdPerEur: number | null | undefined): number | null {
  return usd === null || usd === undefined || !usdPerEur ? null : usd / usdPerEur
}

export type CloreLine =
  | { kind: "off" }
  | { kind: "never" }
  | { kind: "error"; error: string }
  | { kind: "none"; rated: number; best: number | null }
  | { kind: "hits"; rated: number; hits: number; best: number | null }

export function cloreLine(run: CloreRun | null, enabled = true): CloreLine {
  if (!enabled) return { kind: "off" }
  if (!run) return { kind: "never" }
  if (!run.ok) return { kind: "error", error: run.error || "?" }
  if (!run.hits) return { kind: "none", rated: run.rated, best: run.best_roi }
  return { kind: "hits", rated: run.rated, hits: run.hits, best: run.best_roi }
}
