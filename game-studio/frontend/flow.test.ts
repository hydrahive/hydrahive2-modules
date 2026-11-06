import { describe, expect, it } from "vitest"
import { completedStep, highestAvailableStep } from "./flow"
import type { GameDraft } from "./types"

const draft = (changes: Partial<GameDraft> = {}): GameDraft => ({
  draft_id: "draft-a",
  entry_kind: "new",
  title: "Leuchtturm",
  idea: "Ein Leuchtfeuer im Sturm erhalten.",
  genre: "Puzzle",
  target_platform: "desktop",
  core_action: "Brennstoff verteilen",
  success_condition: "Das Schiff erreicht den Hafen",
  current_step: 1,
  revision: 1,
  created_at: "now",
  updated_at: "now",
  ...changes,
})

describe("Game-Studio-Flow", () => {
  it("schaltet Schritte nur nach echten Eingaben frei", () => {
    expect(highestAvailableStep(draft({ title: "", idea: "" }))).toBe(1)
    expect(highestAvailableStep(draft({ genre: "" }))).toBe(2)
    expect(highestAvailableStep(draft({ core_action: "", success_condition: "" }))).toBe(3)
    expect(highestAvailableStep(draft())).toBe(4)
  })

  it("behauptet ohne Runner nie, dass Build oder Evidenz abgeschlossen sind", () => {
    expect(completedStep(draft(), 4)).toBe(false)
    expect(completedStep(draft(), 5)).toBe(false)
  })
})
