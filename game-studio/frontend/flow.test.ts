import { describe, expect, it } from "vitest"
import { completedStep, FLOW_STEPS, highestAvailableStep } from "./flow"
import type { GameProject } from "./types"

const project = (changes: Partial<GameProject> = {}): GameProject => ({
  project_id: "project-a",
  entry_kind: "new",
  engine: "godot",
  engine_version: "auto",
  engine_project_name: "",
  engine_project_path: "",
  engine_project_ready: false,
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
  sharing: { enabled: true, share_name: "Leuchtturm", user: "hydrahive-share", platform: "linux" },
  ...changes,
})

describe("Game-Studio-Flow", () => {
  it("schaltet Schritte nur nach echten Workspace-Inhalten frei", () => {
    expect(highestAvailableStep(project({ title: "", idea: "" }))).toBe(1)
    expect(highestAvailableStep(project({ genre: "" }))).toBe(2)
    expect(highestAvailableStep(project({ core_action: "", success_condition: "" }))).toBe(3)
    expect(highestAvailableStep(project())).toBe(4)
  })

  it("endet nach vier echten Schritten mit dem Samba-Workspace", () => {
    expect(FLOW_STEPS).toEqual(["idea", "brief", "slice", "ready"])
    expect(completedStep(project(), 4)).toBe(false)
  })
})
