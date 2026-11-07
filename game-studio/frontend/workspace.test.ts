import { describe, expect, it } from "vitest"
import { clampWidth, DOCK_MIN, readDock } from "./dock"
import { setupComplete } from "./flow"
import { tabById, WORKSPACE_TABS } from "./tabs/registry"
import type { GameProject } from "./types"

const project = (changes: Partial<GameProject> = {}): GameProject => ({
  project_id: "p", entry_kind: "new", engine: "unreal", engine_version: "auto",
  engine_project_name: "", engine_project_path: "", engine_project_ready: false, last_engine_run: null,
  title: "T", idea: "I", genre: "G", target_platform: "desktop", core_action: "A", success_condition: "S",
  current_step: 4, revision: 1, created_at: "now", updated_at: "now",
  sharing: { enabled: true, share_name: "s", user: "u", platform: "linux" },
  ...changes,
})

describe("Arbeitsfläche", () => {
  it("hat eindeutige Tab-IDs und fällt auf den ersten Tab zurück", () => {
    const ids = WORKSPACE_TABS.map((tab) => tab.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(tabById("design").id).toBe("design")
    expect(tabById("unbekannt").id).toBe(WORKSPACE_TABS[0].id)
    expect(tabById(null).id).toBe(WORKSPACE_TABS[0].id)
  })

  it("öffnet Unreal erst nach erzeugtem Engine-Projekt die Arbeitsfläche", () => {
    expect(setupComplete(project())).toBe(false)
    expect(setupComplete(project({ engine_project_ready: true }))).toBe(true)
  })

  it("öffnet Godot/Unity nach vollständiger Einrichtung die Arbeitsfläche", () => {
    expect(setupComplete(project({ engine: "godot" }))).toBe(true)
    expect(setupComplete(project({ engine: "unity", current_step: 3 }))).toBe(false)
    expect(setupComplete(project({ engine: "godot", core_action: "" }))).toBe(false)
  })

  it("begrenzt die Chatbreite und übersteht kaputten Speicher", () => {
    expect(clampWidth(10, 1600)).toBe(DOCK_MIN)
    expect(clampWidth(5000, 1600)).toBe(960)
    expect(readDock("kaputt", 1600)).toEqual({ open: false, width: 480 })
    expect(readDock(JSON.stringify({ open: true, width: 500 }), 1600)).toEqual({ open: true, width: 500 })
  })
})
