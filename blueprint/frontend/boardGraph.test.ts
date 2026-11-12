import type { Edge } from "@xyflow/react"
import { describe, expect, it } from "vitest"
import { cleanGraph, filterBoards, graphSignature, linkedBoard, parseGraph, projectShowing, proposalDiff } from "./boardGraph"
import type { BoardListItem, BPNode } from "./types"

function node(id: string, label: string, subtype = "action", extra: Record<string, unknown> = {}): BPNode {
  return { id, type: "flowNode", position: { x: 0, y: 0 }, data: { kind: "flow", subtype, label, note: "" }, ...extra } as BPNode
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
      nodes: [node("a", "A", "action", { selected: true, dragging: false, resizing: false, measured: { width: 210, height: 64 } })],
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
    const mine = { nodes: [node("x1", "Start", "event"), node("x2", "Speichern"), node("x3", "Alte Anzeige", "display")], edges: [] }
    const proposal = {
      nodes: [node("start", "start ", "event"), node("save", "Speichern"), node("check", "Gültig?", "condition"), node("err", "Fehler", "display")],
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
    const diff = proposalDiff({ nodes: [node("a", "Liste", "display")], edges: [] }, { nodes: [node("b", "Liste", "action")], edges: [] })
    expect(diff).toMatchObject({ kept: 0, added: ["Liste"], removed: ["Liste"] })
  })
})

describe("Direktlink und Projektfilter", () => {
  const board = (id: number, project_id: string | null): BoardListItem =>
    ({ id, name: `Board ${id}`, project_id, created_at: "", updated_at: "", has_proposal: false })

  it("liest nur eine saubere Board-ID aus dem Verweis", () => {
    expect(linkedBoard("12")).toBe(12)
    for (const bad of ["", " ", "abc", "1.5", "-3", "0", "12abc", "99999999999999999999", null, undefined]) {
      expect(linkedBoard(bad), String(bad)).toBeNull()
    }
  })

  it("filtert nach Projekt, „ohne Projekt“ und „alle“", () => {
    const boards = [board(1, "p-a"), board(2, null), board(3, "p-b")]
    expect(filterBoards(boards, "all").map((b) => b.id)).toEqual([1, 2, 3])
    expect(filterBoards(boards, "none").map((b) => b.id)).toEqual([2])
    expect(filterBoards(boards, "p-a").map((b) => b.id)).toEqual([1])
  })

  it("öffnet den Filter nur, wenn er das verlinkte Board ausblenden würde", () => {
    expect(projectShowing(board(1, "p-a"), "p-a")).toBe("p-a")
    expect(projectShowing(board(1, "p-a"), "all")).toBe("all")
    expect(projectShowing(board(1, "p-a"), "p-b")).toBe("all")
    expect(projectShowing(board(2, null), "none")).toBe("none")
    expect(projectShowing(board(2, null), "p-a")).toBe("all")
  })
})
