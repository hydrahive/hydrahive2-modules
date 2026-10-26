import { describe, expect, it } from "vitest"
import { TABS, dirtyTabs, invalidTabs, tabFromParam } from "./tabs"
import type { VitrineConfig } from "./api"
import { DEFAULT_DASHBOARD } from "./dashLayout"
import { DEFAULT_LIGHT } from "./light"

const base: VitrineConfig = {
  rules: [], default_videos: [], night: { enabled: false, from: "23:00", to: "07:00", mode: "dim" },
  rotate_minutes: 10, fps: 24, message_seconds: 15, dashboard_return_seconds: 120,
  dashboard: { ...DEFAULT_DASHBOARD }, light: structuredClone(DEFAULT_LIGHT),
}
const copy = () => structuredClone(base)

describe("Reiter der Vitrine-Seite", () => {
  it("feste Reihenfolge, unbekannt → Übersicht", () => {
    expect(TABS).toEqual(["overview", "program", "display", "dashboard", "light", "bluetooth"])
    expect(tabFromParam("light")).toBe("light")
    expect(tabFromParam(null)).toBe("overview")
    expect(tabFromParam("<script>")).toBe("overview")
  })

  it("ungespeicherte Änderungen landen beim richtigen Reiter", () => {
    expect(dirtyTabs(base, copy())).toEqual([])
    const c = copy(); c.fps = 30; c.night.enabled = true
    expect(dirtyTabs(base, c)).toEqual(["display"])
    const r = copy(); r.default_videos = ["a.mp4"]
    expect(dirtyTabs(base, r)).toEqual(["program"])
    const l = copy(); l.light!.brightness = 50; l.dashboard.chat_enabled = false
    expect(dirtyTabs(base, l)).toEqual(["dashboard", "light"])
  })

  it("ohne gespeicherten Stand nichts markieren", () => {
    expect(dirtyTabs(null, copy())).toEqual([])
  })

  it("ungültige Werte landen beim richtigen Reiter", () => {
    expect(invalidTabs(base)).toEqual([])
    const l = copy(); l.light!.brightness = 101
    expect(invalidTabs(l)).toEqual(["light"])
    const d = copy(); d.dashboard.messages_max = 9
    expect(invalidTabs(d)).toEqual(["dashboard"])
    const p = copy(); p.rules = [{ id: "a", name: "", kind: "range", enabled: true, priority: 1, videos: [], from: "x", to: "y" }]
    expect(invalidTabs(p)).toEqual(["program"])
  })
})
