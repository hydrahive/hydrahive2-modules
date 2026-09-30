import { useState } from "react"
import { ReactFlowProvider } from "@xyflow/react"
import { Copy } from "lucide-react"
import { boardText } from "./boardText"
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
  const [copied, setCopied] = useState<"" | "ok" | "fail">("")
  // Board als Text in die Zwischenablage — gleicher Text wie das Agent-Tool blueprint_read.
  async function copyAsText() {
    try {
      await navigator.clipboard.writeText(boardText(boardName, b.nodes, b.edges))
      setCopied("ok")
    } catch {
      setCopied("fail")
    }
    setTimeout(() => setCopied(""), 2000)
  }
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center gap-3 border-b border-white/8 px-4 py-2.5">
        <span className="text-sm font-medium text-zinc-200">{boardName}</span>
        <span className="text-xs text-zinc-600">{b.saved ? "gespeichert" : "speichert…"}</span>
        <button
          type="button"
          onClick={() => void copyAsText()}
          title="Board als Text kopieren, zum Einfügen in einen Chat"
          className="ml-auto flex items-center gap-1.5 rounded-md border border-white/10 px-2 py-1 text-xs text-zinc-300 hover:bg-white/5"
        >
          <Copy size={13} />
          {copied === "ok" ? "Kopiert" : copied === "fail" ? "Kopieren nicht möglich" : "Als Text kopieren"}
        </button>
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
