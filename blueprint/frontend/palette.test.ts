import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/module-icon", () => ({ moduleIcon: () => () => null }))
import { nodeTypeFor, NODE_TYPES } from "./nodes"
import { hasPlaceholder, iconOf, kindOf, labelOf, PALETTE } from "./palette-data"

describe("Palette", () => {
  it("hat drei Gruppen: Layout, Funktion, Aufbau", () => {
    expect(PALETTE.map((group) => group.kind)).toEqual(["layout", "flow", "build"])
    expect(PALETTE[2].label).toBe("Aufbau")
  })

  it("kennt die Aufbau-Bausteine", () => {
    expect(PALETTE[2].items.map((item) => item.subtype)).toEqual(["module", "interface", "database", "file", "agent_tool"])
    for (const item of PALETTE[2].items) {
      expect(kindOf(item.subtype)).toBe("build")
      expect(labelOf(item.subtype)).toBe(item.label)
      expect(iconOf(item.subtype)).toBe(item.icon)
      expect(hasPlaceholder(item.subtype)).toBe(false)
    }
  })

  it("jeder Baustein kommt genau einmal vor", () => {
    const all = PALETTE.flatMap((group) => group.items.map((item) => item.subtype))
    expect(new Set(all).size).toBe(all.length)
  })

  it("jede Gruppe hat einen eigenen Knotentyp, den die Zeichenfläche kennt", () => {
    expect(nodeTypeFor("layout")).toBe("layoutNode")
    expect(nodeTypeFor("flow")).toBe("flowNode")
    expect(nodeTypeFor("build")).toBe("buildNode")
    for (const group of PALETTE) expect(NODE_TYPES).toHaveProperty(nodeTypeFor(group.kind))
  })
})
