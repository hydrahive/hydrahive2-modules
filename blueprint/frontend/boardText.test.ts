import { describe, expect, it } from "vitest"
import type { Edge } from "@xyflow/react"
import { boardText } from "./boardText"
import type { BPNode } from "./types"
import fixture from "./board_text_case.json"

describe("boardText", () => {
  it("liefert denselben Text wie das Agent-Tool (gemeinsame Fixture, Task 9111b283)", () => {
    const g = fixture.graph as unknown as { nodes: BPNode[]; edges: Edge[] }
    expect(boardText(fixture.name, g.nodes, g.edges)).toBe(fixture.expected)
  })

  it("meldet ein leeres Board", () => {
    expect(boardText("x", [], [])).toContain("Das Board ist leer.")
  })
})
