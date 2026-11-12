import type { Edge, Node } from "@xyflow/react"

// kind: "layout" = Seiten-Design-Baustein, "flow" = Funktionsplan-Baustein,
// "build" = Aufbau-Baustein (wie man es bauen könnte). Alle leben auf demselben
// Board und dürfen frei verbunden werden.
export type NodeKind = "layout" | "flow" | "build"

export interface BlueprintNodeData {
  kind: NodeKind
  subtype: string
  label: string
  note: string
  placeholder?: string
  [key: string]: unknown // ReactFlow braucht Index-Signatur
}

export type BPNode = Node<BlueprintNodeData>

export interface BoardMeta {
  id: number
  name: string
  project_id: string | null
  created_at: string
  updated_at: string
}

/** Zeile der Board-Liste: ohne Graphen. */
export interface BoardListItem extends BoardMeta {
  has_proposal: boolean
}

export interface Board extends BoardMeta {
  /** Zählt jede Änderung an graph_json. Beim Speichern nennt die Zeichenfläche den Stand, den sie kennt. */
  revision: number
  graph_json: string
  /** Offener Vorschlag des Agenten neben der Fassung des Nutzers, oder null. */
  proposal_json: string | null
  proposal_note: string | null
  proposal_at: string | null
}

/** Antwort der leichten Abfrage: hat sich die Fassung geändert, liegt ein neuer Vorschlag vor? */
export interface BoardState {
  revision: number
  proposal_at: string | null
}

export type VersionSource = "proposal" | "restore" | "overwrite"

/** Frühere Fassung eines Boards, ohne den Graphen. */
export interface BoardVersion {
  id: number
  source: VersionSource
  node_count: number
  created_at: string
}

export interface ProjectRef {
  id: string
  name: string
}

/** "all" = alle Projekte, "none" = ohne Projekt, sonst eine Projekt-ID. */
export type ProjectFilter = "all" | "none" | (string & {})

export interface Graph {
  nodes: BPNode[]
  edges: Edge[]
}
