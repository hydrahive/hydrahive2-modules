// „Annehmen“ beim Ghostwriter (Spec ghostwriter.md §4): nie still überschreiben – vorhandener Text
// wird vorher als Schnappschuss gesichert; schlägt das fehl, wird nichts eingesetzt. Herkunft = KI-Entwurf.
import { describe, expect, it, vi } from "vitest"
import { acceptGhostText, type AcceptDeps } from "./ghostAccept"
import type { Scene } from "./model"

const scene = (over: Partial<Scene> = {}): Scene =>
  ({ id: "s1", title: "S", summary: "Gregor erwacht.", pov: "", status: "draft", origin: "human", text: "", ...over })

function deps(over: Partial<AcceptDeps> = {}) {
  const log: string[] = []
  const d: AcceptDeps = {
    snapshot: vi.fn(async () => { log.push("snapshot"); return true }),
    replace: vi.fn(() => { log.push("replace") }),
    remember: vi.fn(async () => { log.push("remember") }),
    ...over,
  }
  return { d, log }
}

describe("acceptGhostText", () => {
  it("leere Szene: kein Schnappschuss, Text als KI-Entwurf eingesetzt", async () => {
    const { d, log } = deps()
    expect(await acceptGhostText("  Neuer Text \n", scene(), d)).toBe("accepted")
    expect(log).toEqual(["replace"])
    expect(d.replace).toHaveBeenCalledWith("s1", "Neuer Text", "ai_draft")
  })

  it("Szene mit Text: erst Schnappschuss, dann ersetzen", async () => {
    const { d, log } = deps()
    expect(await acceptGhostText("KI", scene({ text: "Mein Text" }), d)).toBe("accepted")
    expect(log).toEqual(["snapshot", "replace"])
  })

  it("Schnappschuss schlägt fehl: nichts eingesetzt", async () => {
    const { d, log } = deps({ snapshot: vi.fn(async () => false) })
    expect(await acceptGhostText("KI", scene({ text: "Mein Text" }), d)).toBe("snapshot_failed")
    expect(log).toEqual([])
    expect(d.replace).not.toHaveBeenCalled()
  })

  it("leerer Vorschlag: nichts passiert", async () => {
    const { d, log } = deps()
    expect(await acceptGhostText("   ", scene({ text: "Mein Text" }), d)).toBe("empty")
    expect(log).toEqual([])
  })

  it("Gedächtnis nur anstoßen, wenn die Zusammenfassung leer ist", async () => {
    const a = deps()
    await acceptGhostText("KI", scene({ summary: "" }), a.d)
    expect(a.log).toEqual(["replace", "remember"])
    const b = deps()
    await acceptGhostText("KI", scene(), b.d)
    expect(b.d.remember).not.toHaveBeenCalled()
  })

  it("Gedächtnis-Fehler ändert das Ergebnis nicht (Text ist schon übernommen)", async () => {
    const { d } = deps({ remember: vi.fn(async () => { throw new Error("weg") }) })
    expect(await acceptGhostText("KI", scene({ summary: "" }), d)).toBe("accepted")
    expect(d.replace).toHaveBeenCalledOnce()
  })
})
