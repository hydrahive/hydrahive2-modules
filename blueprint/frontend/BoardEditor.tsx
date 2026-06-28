import { ReactFlowProvider } from "@xyflow/react"
import { useBoard } from "./useBoard"
import { NodePalette } from "./NodePalette"
import { Canvas } from "./Canvas"
import { PropertiesPanel } from "./PropertiesPanel"

interface Props {
  boardId: number
  boardName: string
}

function EditorInner({ boardId, boardName }: Props) {
  const b = useBoard(boardId)
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center gap-3 border-b border-white/8 px-4 py-2.5">
        <span className="text-sm font-medium text-zinc-200">{boardName}</span>
        <span className="text-xs text-zinc-600">{b.saved ? "gespeichert" : "speichert…"}</span>
      </div>
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <Canvas
          nodes={b.nodes}
          edges={b.edges}
          onNodesChange={b.onNodesChange}
          onEdgesChange={b.onEdgesChange}
          onConnect={b.onConnect}
          onNodeClick={b.onNodeClick}
          onPaneClick={b.onPaneClick}
          onDrop={b.onDrop}
          onDragOver={b.onDragOver}
        />
        <PropertiesPanel
          node={b.selectedNode}
          onChange={b.updateNodeData}
          onDelete={b.deleteSelected}
        />
      </div>
    </div>
  )
}

export function BoardEditor(props: Props) {
  // ReactFlowProvider pro Board neu (key) → sauberer State beim Wechsel.
  return (
    <ReactFlowProvider key={props.boardId}>
      <EditorInner {...props} />
    </ReactFlowProvider>
  )
}
