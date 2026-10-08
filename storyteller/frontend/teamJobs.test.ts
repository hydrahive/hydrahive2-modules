// T1e – Team-Knöpfe: reine Hilfen (Stelle je Bereich, laufende Aufträge, Nachfragen nur solange etwas läuft).
import { describe, expect, it } from "vitest"
import { activeFor, isActive, needsPolling, placeFor, type TeamJob } from "./teamJobs"

const job = (over: Partial<TeamJob>): TeamJob => ({
  id: "j", job: "check_scene", role: "plausibility", agent_name: "T — Plausibilität", place_id: "s1",
  place_title: "Am Hafen", status: "queued", summary: "", error: "", cost_micros: null, estimate_micros: null,
  limit_tokens: 0, tokens_in: 0, tokens_out: 0,
  session_id: "", at: "2026-10-08T10:00:00+00:00", finished_at: "", ...over,
})

describe("teamJobs", () => {
  it("Stelle: Szene direkt, Kapitel über die Szene", () => {
    const chapters = { c1: ["s1", "s2"], c2: ["s3"] }
    expect(placeFor("scene", "s2", chapters)).toBe("s2")
    expect(placeFor("chapter", "s2", chapters)).toBe("c1")
    expect(placeFor("chapter", "s3", chapters)).toBe("c2")
    expect(placeFor("chapter", "weg", chapters)).toBeNull()
  })
  it("aktiv = queued oder running", () => {
    expect(isActive(job({ status: "queued" }))).toBe(true)
    expect(isActive(job({ status: "running" }))).toBe(true)
    for (const s of ["done", "error", "cancelled", "limit"] as const) expect(isActive(job({ status: s }))).toBe(false)
  })
  it("laufender Auftrag eines Knopfs an dieser Stelle", () => {
    const jobs = [job({ id: "a", status: "done" }), job({ id: "b", status: "running" }),
      job({ id: "c", status: "running", place_id: "s9" })]
    expect(activeFor(jobs, "check_scene", "s1")?.id).toBe("b")
    expect(activeFor(jobs, "edit_scene", "s1")).toBeUndefined()
  })
  it("nachfragen nur, solange etwas läuft", () => {
    expect(needsPolling([job({ status: "done" })])).toBe(false)
    expect(needsPolling([job({ status: "done" }), job({ status: "queued" })])).toBe(true)
    expect(needsPolling(null)).toBe(false)
  })
})
