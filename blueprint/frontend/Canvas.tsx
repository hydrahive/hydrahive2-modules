import React from "react"
import {
  ReactFlow, Background, Controls, MiniMap, BackgroundVariant, Panel,
  type Connection, type Edge, type OnNodesChange, type OnEdgesChange,
} from "@xyflow/react"
import { BUILD_DOT, NODE_TYPES } from "./nodes"
import type { T } from "./texts.de"
import type { BPNode } from "./types"

interface Props {
  nodes: BPNode[]
  edges: Edge[]
  /** Nur ansehen: Vorschau des Vorschlags, oder das Board ist nicht geladen. Nichts lässt sich ändern. */
  readOnly: boolean
  t: T
  // Auch beim Ansehen nötig: Darüber meldet die Zeichenfläche die gemessene Größe der Bausteine.
  onNodesChange: OnNodesChange<BPNode>
  onEdgesChange: OnEdgesChange
  onConnect?: (c: Connection) => void
  onNodeClick?: (e: React.MouseEvent, node: BPNode) => void
  onPaneClick?: () => void
  onDrop?: (e: React.DragEvent) => void
  onDragOver?: (e: React.DragEvent) => void
}

export function Canvas(p: Props) {
  const edit = !p.readOnly
  return (
    <div className="relative min-w-0 flex-1" onDrop={edit ? p.onDrop : undefined}
      onDragOver={edit ? p.onDragOver : undefined}>
      <ReactFlow
        nodes={p.nodes}
        edges={p.edges}
        onNodesChange={p.onNodesChange}
        onEdgesChange={p.onEdgesChange}
        onConnect={edit ? p.onConnect : undefined}
        onNodeClick={edit ? (p.onNodeClick as never) : undefined}
        onPaneClick={p.onPaneClick}
        nodesDraggable={edit}
        nodesConnectable={edit}
        elementsSelectable={edit}
        deleteKeyCode={edit ? "Backspace" : null}
        nodeTypes={NODE_TYPES}
        colorMode="dark"
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{ animated: true, style: { stroke: "#818cf8", strokeWidth: 2 } }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.05)" />
        <Controls showInteractive={false} />
        <MiniMap nodeColor={(n) => (n.type === "layoutNode" ? "#71717a" : n.type === "buildNode" ? BUILD_DOT : "#0ea5e9")} />
        {edit && p.nodes.length === 0 && (
          <Panel position="top-center" style={{ marginTop: 48 }}>
            <div className="pointer-events-none text-center">
              <p className="text-base text-[#9aa7bc]">{p.t("canvas_empty")}</p>
              <p className="mt-1 text-sm text-[#9aa7bc]">{p.t("canvas_empty_hint")}</p>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}
