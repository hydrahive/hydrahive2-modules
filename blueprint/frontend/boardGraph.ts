// Reine Helfer rund um den Board-Graphen: lesen, vergleichen, Vorschlag gegen die eigene Fassung
// stellen. Ohne React und ohne Netz, damit alles direkt testbar ist. Liste und Texte: boardView.ts.
import type { Edge } from "@xyflow/react"
import type { BPNode, Graph } from "./types"

/** Gespeicherter Graph, oder null, wenn er nicht lesbar ist. Unlesbar ist nicht dasselbe wie leer:
 *  Ein unlesbares Board darf die Zeichenfläche nie als leeres Board speichern. */
export function parseGraph(raw: string | null | undefined): Graph | null {
  if (!raw) return null
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return null
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) return null
  const { nodes, edges } = data as { nodes?: unknown; edges?: unknown }
  if (!Array.isArray(nodes)) return null
  return { nodes: nodes as BPNode[], edges: Array.isArray(edges) ? (edges as Edge[]) : [] }
}

/** Der Graph ohne das, was nur die Ansicht betrifft: Auswahl, laufendes Ziehen, gemessene Größe. */
export function cleanGraph(graph: Graph): Graph {
  return {
    nodes: graph.nodes.map((node) => {
      const { selected: _selected, dragging: _dragging, resizing: _resizing, measured: _measured, ...rest } =
        node as BPNode & { resizing?: boolean }
      return rest as BPNode
    }),
    edges: graph.edges.map((edge) => {
      const { selected: _selected, ...rest } = edge
      return rest as Edge
    }),
  }
}

/** Inhalt des Graphen als Text. Gleicher Text heißt: nichts zu speichern. So wird auch gespeichert. */
export function graphSignature(graph: Graph): string {
  return JSON.stringify(cleanGraph(graph))
}

const oneLine = (value: unknown) => String(value ?? "").split(/\s+/).filter(Boolean).join(" ")
const nameOf = (node: BPNode) => oneLine(node.data?.label) || "—"
// Bausteine gelten als gleich, wenn Art und Beschriftung übereinstimmen. Die IDs taugen dafür nicht:
// Der Agent vergibt eigene Kürzel, die Zeichenfläche laufende Nummern.
const matchKey = (node: BPNode) => `${String(node.data?.subtype ?? "")}\u0000${oneLine(node.data?.label).toLowerCase()}`

export interface ProposalDiff {
  nodes: number
  edges: number
  /** Bausteine, die es in der eigenen Fassung schon gibt. */
  kept: number
  /** Beschriftungen der Bausteine, die der Vorschlag neu bringt. */
  added: string[]
  /** Beschriftungen der eigenen Bausteine, die im Vorschlag fehlen. */
  removed: string[]
  /** IDs der neuen Bausteine im Vorschlag, für die Hervorhebung in der Vorschau. */
  freshIds: Set<string>
}

/** Was der Vorschlag gegenüber der eigenen Fassung ändert. */
export function proposalDiff(mine: Graph, proposal: Graph): ProposalDiff {
  const open = new Map<string, number>()
  for (const node of mine.nodes) open.set(matchKey(node), (open.get(matchKey(node)) ?? 0) + 1)
  const take = (node: BPNode) => {
    const left = open.get(matchKey(node)) ?? 0
    if (left > 0) open.set(matchKey(node), left - 1)
    return left > 0
  }
  const added: string[] = []
  const freshIds = new Set<string>()
  let kept = 0
  for (const node of proposal.nodes) {
    if (take(node)) kept += 1
    else {
      added.push(nameOf(node))
      freshIds.add(node.id)
    }
  }
  // Was jetzt noch offen ist, kommt im Vorschlag nicht mehr vor.
  const removed = mine.nodes.filter(take).map(nameOf)
  return { nodes: proposal.nodes.length, edges: proposal.edges.length, kept, added, removed, freshIds }
}

const FRESH = { outline: "2px solid #69d7ff", outlineOffset: 4, borderRadius: 14 }

/** Bausteine des Vorschlags für die Vorschau: Die neuen bekommen einen Rahmen. Der Vorschlag bleibt, wie er ist. */
export function previewNodes(nodes: readonly BPNode[], freshIds: ReadonlySet<string>): BPNode[] {
  return nodes.map((node) => (freshIds.has(node.id) ? { ...node, style: { ...node.style, ...FRESH } } : node))
}
