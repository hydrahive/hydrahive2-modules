// Ghostwriter G4 – Hilfen für den Chat-Modus ohne React: Vorschlags-Markierungen, Werkzeuge ergänzen.
import { describe, expect, it } from "vitest"
import { proposalMarks, withTools } from "./chatApi"

describe("chatApi", () => {
  it("macht aus der Vorschlagsliste Markierungen je Szene, Herkunft mit Vorgabe", () => {
    expect(proposalMarks([
      { scene_id: "a", run_id: "", model: "", base_version: 2, words: 40, at: "t1", source: "agent", session_id: "s", note: "kürzer" },
      { scene_id: "b", run_id: "r", model: "m", base_version: 1, words: 9, at: "t2" },
    ])).toEqual({
      a: { words: 40, model: "", at: "t1", source: "agent", note: "kürzer" },
      b: { words: 9, model: "m", at: "t2", source: "run", note: "" },
    })
    expect(proposalMarks([])).toEqual({})
  })
  it("ergänzt fehlende Werkzeuge ohne Doppelte und ohne die Reihenfolge zu ändern", () => {
    expect(withTools(["file_read", "storyteller_books"], ["storyteller_books", "storyteller_read"]))
      .toEqual(["file_read", "storyteller_books", "storyteller_read"])
    expect(withTools([], ["x"])).toEqual(["x"])
  })
})
