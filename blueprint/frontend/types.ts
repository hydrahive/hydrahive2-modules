import type { Edge, Node } from "@xyflow/react"

// kind: "layout" = Seiten-Design-Baustein, "flow" = Funktionsplan-Baustein.
// Beide leben auf demselben Board und dürfen frei verbunden werden.
export interface BlueprintNodeData {
  kind: "layout" | "flow"
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
  created_at: string
  updated_at: string
}

export interface Board extends BoardMeta {
  graph_json: string
}

export interface Graph {
  nodes: BPNode[]
  edges: Edge[]
}
