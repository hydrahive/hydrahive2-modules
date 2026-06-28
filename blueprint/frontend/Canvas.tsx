import React from "react"
import {
  ReactFlow, Background, Controls, MiniMap, BackgroundVariant, Panel,
  type Connection, type Edge, type OnNodesChange, type OnEdgesChange,
} from "@xyflow/react"
import { NODE_TYPES } from "./nodes"
import type { BPNode } from "./types"

interface Props {
  nodes: BPNode[]
  edges: Edge[]
  onNodesChange: OnNodesChange<BPNode>
  onEdgesChange: OnEdgesChange
  onConnect: (c: Connection) => void
  onNodeClick: (e: React.MouseEvent, node: BPNode) => void
  onPaneClick: () => void
  onDrop: (e: React.DragEvent) => void
  onDragOver: (e: React.DragEvent) => void
}

export function Canvas(p: Props) {
  return (
    <div className="relative flex-1" onDrop={p.onDrop} onDragOver={p.onDragOver}>
      <ReactFlow
        nodes={p.nodes}
        edges={p.edges}
        onNodesChange={p.onNodesChange}
        onEdgesChange={p.onEdgesChange}
        onConnect={p.onConnect}
        onNodeClick={p.onNodeClick as never}
        onPaneClick={p.onPaneClick}
        nodeTypes={NODE_TYPES}
        colorMode="dark"
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{ animated: true, style: { stroke: "#818cf8", strokeWidth: 2 } }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.05)" />
        <Controls />
        <MiniMap nodeColor={(n) => (n.type === "layoutNode" ? "#71717a" : "#0ea5e9")} />
        {p.nodes.length === 0 && (
          <Panel position="top-center" style={{ marginTop: 48 }}>
            <div className="pointer-events-none text-center">
              <p className="text-base text-white/25">Bausteine von links aufs Board ziehen</p>
              <p className="mt-1 text-sm text-white/15">Andockpunkte verbinden · Baustein anklicken zum Beschriften</p>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}
