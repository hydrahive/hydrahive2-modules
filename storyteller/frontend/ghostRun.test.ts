// Ein Ghostwriter-Lauf (Start → Speichern → Stream): Abbrechen muss in JEDER Phase wirken,
// auch während vorher noch gespeichert wird (Befund hydratest 07.10.).
import { describe, expect, it, vi } from "vitest"
import { StoryApiError } from "./api"
import { runGhost, type RunDeps } from "./ghostRun"

const deferred = () => {
  let resolve!: () => void
  const promise = new Promise<void>((r) => { resolve = r })
  return { promise, resolve }
}

function deps(over: Partial<RunDeps> = {}): RunDeps {
  return {
    flush: vi.fn(async () => {}),
    stream: vi.fn(async (onText: (t: string) => void) => { onText("Eins "); onText("zwei"); return { words: 2, model: "m", mode: "proposal" as const } }),
    ...over,
  }
}

describe("runGhost", () => {
  it("normaler Lauf: erst speichern, dann streamen, Text gesammelt", async () => {
    const order: string[] = []
    const d = deps({
      flush: vi.fn(async () => { order.push("flush") }),
      stream: vi.fn(async (onText: (t: string) => void) => { order.push("stream"); onText("A"); onText("B"); return { words: 1, model: "m", mode: "proposal" as const } }),
    })
    const seen: string[] = []
    const r = await runGhost(d, new AbortController(), (t) => seen.push(t))
    expect(order).toEqual(["flush", "stream"])
    expect(r).toMatchObject({ kind: "done", text: "AB", done: { words: 1 } })
    expect(seen).toEqual(["A", "AB"])
  })

  it("Abbrechen WÄHREND des Speicherns: kein Stream, Ergebnis abgebrochen ohne Text", async () => {
    const gate = deferred()
    const d = deps({ flush: vi.fn(() => gate.promise) })
    const ctrl = new AbortController()
    const p = runGhost(d, ctrl, () => {})
    ctrl.abort()
    gate.resolve()
    expect(await p).toEqual({ kind: "aborted", text: "" })
    expect(d.stream).not.toHaveBeenCalled()
  })

  it("Abbrechen während des Streams: bisheriger Text bleibt", async () => {
    const ctrl = new AbortController()
    const d = deps({
      stream: vi.fn(async (onText: (t: string) => void) => { onText("Halb "); ctrl.abort(); throw new StoryApiError(0, "aborted") }),
    })
    expect(await runGhost(d, ctrl, () => {})).toEqual({ kind: "aborted", text: "Halb " })
  })

  it("Fehler vom Server wird weitergereicht, Text bis dahin bleibt", async () => {
    const d = deps({ stream: vi.fn(async (onText: (t: string) => void) => { onText("x"); throw new StoryApiError(409, "ai_busy") }) })
    const r = await runGhost(d, new AbortController(), () => {})
    expect(r.kind).toBe("error")
    expect(r.kind === "error" && r.error.code).toBe("ai_busy")
    expect(r.text).toBe("x")
  })

  it("unbekannter Fehler wird zu llm_failed", async () => {
    const d = deps({ stream: vi.fn(async () => { throw new TypeError("kaputt") }) })
    const r = await runGhost(d, new AbortController(), () => {})
    expect(r.kind === "error" && r.error.code).toBe("llm_failed")
  })
})
