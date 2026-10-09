// A2/A3 – reine Hilfen: Herkunft lesbar, Rückkehrort einer Szene, Reihenfolge der Bücher im Papierkorb.
import { describe, expect, it } from "vitest"
import { originLabel } from "./proposalHistory"
import { canDeleteChapter, sceneDeleteKind, sortBooks, whereBack, type TrashBook, type TrashScene } from "./trashApi"

const t = (k: string) => ({ history_from_agent: "Agent", history_from_run: "Ghostwriter-Lauf" }[k] ?? k)

const scene = (over: Partial<TrashScene>): TrashScene => ({
  id: "x", scene_id: "s", title: "T", summary: "", words: 0, deleted_at: "", chapter_id: "c", chapter_title: "K",
  after: "", chapter_exists: true, ...over,
})
const book = (over: Partial<TrashBook>): TrashBook => ({
  id: "b-1", kind: "deleted", book_id: "b", title: "B", scenes: 1, words: 1, deleted_at: "2026-10-01T00:00:00+00:00",
  restorable: true, ...over,
})

describe("Herkunft", () => {
  it("Agent-Name ohne Buchtitel, sonst Lauf/Agent", () => {
    expect(originLabel({ author: "Der Leuchtturm — Lektor" }, t)).toBe("Lektor")
    expect(originLabel({ author: "Ghostwriter-Lauf" }, t)).toBe("Ghostwriter-Lauf")
    expect(originLabel({ author: "", source: "agent" }, t)).toBe("Agent")
    expect(originLabel({ source: "run" }, t)).toBe("Ghostwriter-Lauf")
  })
})

describe("Papierkorb", () => {
  it("Szene kehrt an alte Stelle zurück, wenn es das Kapitel noch gibt", () => {
    expect(whereBack(scene({ chapter_exists: true }))).toBe("original")
    expect(whereBack(scene({ chapter_exists: false }))).toBe("end")
  })
  it("Bücher: gelöschte zuerst (neueste oben), Umzugs-Sicherungen unten", () => {
    const rows = [book({ id: "m", kind: "moved", deleted_at: "2026-10-09T00:00:00+00:00", restorable: false }),
      book({ id: "alt", deleted_at: "2026-09-01T00:00:00+00:00" }), book({ id: "neu", deleted_at: "2026-10-08T00:00:00+00:00" })]
    expect(sortBooks(rows).map((r) => r.id)).toEqual(["neu", "alt", "m"])
  })
})

describe("Löschen (C1)", () => {
  it("Szene: einzeln, wenn das Kapitel weitere hat; sonst geht das Kapitel mit; letzte des Buchs bleibt", () => {
    expect(sceneDeleteKind(3, 2)).toBe("scene")
    expect(sceneDeleteKind(1, 2)).toBe("scene")
    expect(sceneDeleteKind(3, 1)).toBe("chapter")
    expect(sceneDeleteKind(2, 1)).toBe("chapter")
    expect(sceneDeleteKind(1, 1)).toBe("blocked")
  })
  it("Kapitel: nur wenn das Buch noch ein weiteres hat", () => {
    expect(canDeleteChapter(2)).toBe(true)
    expect(canDeleteChapter(1)).toBe(false)
  })
})
