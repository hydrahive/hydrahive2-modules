// T1a (Task 29fb3911): Vorschlag deutlich kürzer als die Szene → Warnung im Hinweis über dem Editor.
import { describe, expect, it } from "vitest"
import { markOf, shrinks } from "./proposalMark"

describe("proposalMark", () => {
  it("nimmt die Wortzahl der Szene mit, ältere Vorschläge ohne Feld gelten als 0", () => {
    expect(markOf({ scene_id: "a", run_id: "", model: "", base_version: 2, words: 40, at: "t", source: "agent", note: "n", scene_words: 100 }))
      .toEqual({ words: 40, model: "", at: "t", source: "agent", note: "n", sceneWords: 100, author: "", replacedFrom: "" })
    expect(markOf({ scene_id: "b", run_id: "r", model: "m", base_version: 1, words: 9, at: "t2" }))
      .toEqual({ words: 9, model: "m", at: "t2", source: "run", note: "", sceneWords: 0, author: "", replacedFrom: "" })
  })
  it("A2: merkt sich den Agenten und wessen Vorschlag ersetzt wurde", () => {
    const m = markOf({ scene_id: "a", run_id: "", model: "", base_version: 2, words: 40, at: "t", source: "agent",
      author: "Buch — Lektor", replaced_from: { source: "run", author: "Ghostwriter-Lauf", at: "t0" } })
    expect(m.author).toBe("Buch — Lektor")
    expect(m.replacedFrom).toBe("Ghostwriter-Lauf")
    expect(markOf({ scene_id: "a", run_id: "", model: "", base_version: 2, words: 40, at: "t", replaced_from: null }).replacedFrom).toBe("")
  })
  it("warnt nur, wenn der Vorschlag unter der Hälfte der Szene liegt", () => {
    expect(shrinks({ words: 30, model: "", at: "", sceneWords: 100 })).toBe(true)
    expect(shrinks({ words: 50, model: "", at: "", sceneWords: 100 })).toBe(false)
    expect(shrinks({ words: 5, model: "", at: "", sceneWords: 0 })).toBe(false)
    expect(shrinks({ words: 5, model: "", at: "" })).toBe(false)
  })
})
