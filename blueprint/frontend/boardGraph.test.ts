import type { Edge } from "@xyflow/react"
import { describe, expect, it } from "vitest"
import { cleanGraph, graphSignature, parseGraph, previewNodes, proposalDiff } from "./boardGraph"
import type { BPNode } from "./types"

function node(id: string, label: string, subtype = "action", extra: Record<string, unknown> = {}): BPNode {
  const data = { kind: "flow", subtype, label, note: "" }
  return { id, type: "flowNode", position: { x: 0, y: 0 }, data, ...extra } as BPNode
}
const edge = (source: string, target: string): Edge => ({ id: `${source}-${target}`, source, target })

describe("parseGraph", () => {
  it("liest einen gespeicherten Graphen", () => {
    const graph = parseGraph(JSON.stringify({ nodes: [node("a", "A")], edges: [] }))
    expect(graph?.nodes.map((n) => n.id)).toEqual(["a"])
  })

  it("Unlesbares ist nicht dasselbe wie leer", () => {
    for (const raw of ["{kaputt", "null", "[]", '{"nodes": 5, "edges": []}', '{"edges": []}', "", null, undefined]) {
      expect(parseGraph(raw), String(raw)).toBeNull()
    }
    expect(parseGraph('{"nodes":[],"edges":[]}')).toEqual({ nodes: [], edges: [] })
  })

  it("fehlende Verbindungen gelten als keine", () => {
    expect(parseGraph('{"nodes":[]}')).toEqual({ nodes: [], edges: [] })
  })
})

describe("graphSignature", () => {
  it("Auswahl, Ziehen und gemessene Größe sind kein Inhalt", () => {
    const plain = { nodes: [node("a", "A")], edges: [edge("a", "b")] }
    const touched = {
      nodes: [node("a", "A", "action", {
        selected: true, dragging: false, resizing: false, measured: { width: 210, height: 64 },
      })],
      edges: [{ ...edge("a", "b"), selected: true }],
    }
    expect(graphSignature(touched)).toBe(graphSignature(plain))
    expect(cleanGraph(touched)).toEqual(plain)
  })

  it("Position, Größe, Beschriftung und Verbindungen sind Inhalt", () => {
    const base = { nodes: [node("a", "A"), node("b", "B")], edges: [edge("a", "b")] }
    const moved = { ...base, nodes: [{ ...base.nodes[0], position: { x: 15, y: 0 } }, base.nodes[1]] }
    const resized = { ...base, nodes: [{ ...base.nodes[0], width: 300 }, base.nodes[1]] }
    const renamed = { ...base, nodes: [node("a", "Anders"), base.nodes[1]] }
    const unlinked = { ...base, edges: [] }
    for (const changed of [moved, resized, renamed, unlinked]) expect(graphSignature(changed)).not.toBe(graphSignature(base))
  })

  it("ändert den übergebenen Graphen nicht", () => {
    const graph = { nodes: [node("a", "A", "action", { selected: true })], edges: [] }
    cleanGraph(graph)
    expect(graph.nodes[0].selected).toBe(true)
  })
})

describe("proposalDiff", () => {
  it("vergleicht nach Art und Beschriftung, nicht nach ID", () => {
    const mine = {
      nodes: [node("x1", "Start", "event"), node("x2", "Speichern"), node("x3", "Alte Anzeige", "display")], edges: [],
    }
    const proposal = {
      nodes: [
        node("start", "start ", "event"), node("save", "Speichern"),
        node("check", "Gültig?", "condition"), node("err", "Fehler", "display"),
      ],
      edges: [edge("start", "save"), edge("save", "check")],
    }
    const diff = proposalDiff(mine, proposal)
    expect(diff).toMatchObject({ nodes: 4, edges: 2, kept: 2, added: ["Gültig?", "Fehler"], removed: ["Alte Anzeige"] })
    expect([...diff.freshIds]).toEqual(["check", "err"])
  })

  it("zählt gleiche Bausteine einzeln", () => {
    const mine = { nodes: [node("a", "Knopf"), node("b", "Knopf")], edges: [] }
    const one = proposalDiff(mine, { nodes: [node("k", "Knopf")], edges: [] })
    expect(one).toMatchObject({ kept: 1, added: [], removed: ["Knopf"] })
    const three = proposalDiff(mine, { nodes: [node("k1", "Knopf"), node("k2", "Knopf"), node("k3", "Knopf")], edges: [] })
    expect(three).toMatchObject({ kept: 2, added: ["Knopf"], removed: [] })
  })

  it("gleiche Beschriftung mit anderer Art ist ein anderer Baustein", () => {
    const mine = { nodes: [node("a", "Liste", "display")], edges: [] }
    const diff = proposalDiff(mine, { nodes: [node("b", "Liste", "action")], edges: [] })
    expect(diff).toMatchObject({ kept: 0, added: ["Liste"], removed: ["Liste"] })
  })
})

describe("previewNodes", () => {
  it("hebt nur die neuen Bausteine hervor und ändert den Vorschlag nicht", () => {
    const nodes = [node("alt", "Alt"), node("neu", "Neu", "action", { style: { width: 240 } })]
    const shown = previewNodes(nodes, new Set(["neu"]))
    expect(shown[0]).toBe(nodes[0])
    expect(shown[1].style).toMatchObject({ width: 240, outline: expect.stringContaining("solid") })
    expect(nodes[1].style).toEqual({ width: 240 })
  })
})
