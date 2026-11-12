// Reine Helfer rund um den Board-Graphen: lesen, vergleichen, Vorschlag gegen die eigene Fassung
// stellen, Direktlink und Projektfilter. Ohne React und ohne Netz, damit alles direkt testbar ist.
import type { Edge } from "@xyflow/react"
import type { BoardListItem, BPNode, Graph, ProjectFilter } from "./types"

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

/** Board-ID aus /blueprint?board=<id>. Alles andere als eine saubere Zahl zählt nicht. */
export function linkedBoard(value: string | null | undefined): number | null {
  return value && /^[1-9]\d{0,14}$/.test(value) ? Number(value) : null
}

export function filterBoards<T extends { project_id: string | null }>(boards: readonly T[], project: ProjectFilter): T[] {
  if (project === "all") return [...boards]
  return boards.filter((board) => (project === "none" ? board.project_id === null : board.project_id === project))
}

/** Filter, mit dem dieses Board in der Liste steht: bleibt, wenn er passt, sonst „alle“. */
export function projectShowing(board: Pick<BoardListItem, "project_id">, current: ProjectFilter): ProjectFilter {
  return filterBoards([board], current).length > 0 ? current : "all"
}

/** Zeitstempel des Servers als Datum mit Uhrzeit in der Sprache der Oberfläche. */
export function formatStamp(value: string | null | undefined, locale: string): string {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return value ?? ""
  return date.toLocaleString(locale.startsWith("de") ? "de" : "en", { dateStyle: "medium", timeStyle: "short" })
}
