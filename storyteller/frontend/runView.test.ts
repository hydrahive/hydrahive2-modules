// Lauf-Anzeige (Ghostwriter G2) ohne React: Zählen, Ende erkennen, welche Szenen neu geladen werden müssen.
import { describe, expect, it } from "vitest"
import { costLabel, isFinished, progressCounts, scenesToReload, type RunInfo } from "./runView"

const run = (over: Partial<RunInfo> = {}): RunInfo => ({
  id: "r", status: "running", scope: "book", model: "m", current_scene: "s2", tokens_in: 0, tokens_out: 0,
  cost_micros: null, cost_partial: false, error: null, options: {},
  progress: [
    { scene_id: "s1", state: "written", words: 800 },
    { scene_id: "s2", state: "writing" },
    { scene_id: "s3", state: "waiting" },
    { scene_id: "s4", state: "proposal", words: 700 },
    { scene_id: "s5", state: "skipped_filled" },
  ],
  ...over,
})

describe("runView", () => {
  it("zählt fertig/Vorschlag/übersprungen/offen", () => {
    expect(progressCounts(run())).toEqual({ total: 5, written: 1, proposals: 1, skipped: 1, errors: 0, open: 2, words: 1500 })
  })
  it("erkennt das Ende", () => {
    expect(isFinished(run())).toBe(false)
    expect(isFinished(run({ status: "queued" }))).toBe(false)
    for (const s of ["done", "cancelled", "limit", "error"] as const) expect(isFinished(run({ status: s }))).toBe(true)
    expect(isFinished(null)).toBe(true)
  })
  it("lädt nur Szenen nach, die seit dem letzten Stand fertig geschrieben wurden", () => {
    const before = run({ progress: [{ scene_id: "s1", state: "writing" }, { scene_id: "s2", state: "waiting" }] })
    const after = run({ progress: [{ scene_id: "s1", state: "written", words: 5 }, { scene_id: "s2", state: "proposal", words: 3 }] })
    expect(scenesToReload(before, after)).toEqual({ written: ["s1"], proposals: ["s2"] })
    expect(scenesToReload(after, after)).toEqual({ written: [], proposals: [] })
    expect(scenesToReload(null, after)).toEqual({ written: ["s1"], proposals: ["s2"] })
  })
  it("Kosten: Cent mit zwei Stellen, unbekannt → null, teilweise → mit Hinweis", () => {
    expect(costLabel(null, false)).toBeNull()
    expect(costLabel(123456, false)).toEqual({ cents: "123.46", partial: false })
    expect(costLabel(800, true)).toEqual({ cents: "0.80", partial: true })
  })
})
