import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  addEdge, useEdgesState, useNodesState, useReactFlow,
  type Connection, type Edge,
} from "@xyflow/react"
import { blueprintApi } from "./api"
import { BoardSync } from "./boardSync"
import { kindOf, labelOf, hasPlaceholder } from "./palette-data"
import { nodeTypeFor } from "./nodes"
import type { Board, BPNode, SyncStatus } from "./types"

let _seq = 0
const genId = (s: string) => `${s}-${++_seq}-${Date.now()}`
// In diesen Zuständen ist das Board geladen: Nur dann lässt sich zeichnen.
const EDITABLE: readonly SyncStatus[] = ["saved", "saving", "save_error", "conflict"]

/** Was die Oberfläche am Abgleich auslösen kann (boardSync.ts). */
export interface BoardActions {
  retry: () => Promise<void>
  keepMine: () => Promise<void>
  takeTheirs: () => Promise<void>
  /** Erst die eigene Fassung speichern, dann die Aktion. false: Speichern ging nicht, die Aktion lief nicht. */
  apply: (action: () => Promise<Board>) => Promise<boolean>
  adopt: (board: Board) => void
  poll: () => Promise<void>
}

/** Zeichenfläche eines Boards. Laden, Speichern und die Abfrage nach Neuem macht boardSync.ts. */
export function useBoard(boardId: number, onBoard: (board: Board) => void) {
  const [nodes, setNodes, onNodesChange] = useNodesState<BPNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [status, setStatus] = useState<SyncStatus>("loading")
  const [board, setBoard] = useState<Board | null>(null)
  const rf = useReactFlow()
  const sync = useRef<BoardSync | null>(null)
  // rf und onBoard wechseln ihre Identität, ohne dass der Abgleich neu starten soll.
  const latest = useRef({ rf, onBoard })
  useEffect(() => { latest.current = { rf, onBoard } }, [rf, onBoard])

  useEffect(() => {
    const created = new BoardSync(boardId, blueprintApi, {
      onGraph: (graph) => {
        setNodes(graph.nodes)
        setEdges(graph.edges)
        setSelectedId(null)
        if (graph.nodes.length > 0) void latest.current.rf.fitView()
      },
      onStatus: setStatus,
      onBoard: (next) => { setBoard(next); latest.current.onBoard(next) },
    }, { isVisible: () => document.visibilityState === "visible" })
    sync.current = created
    void created.start()
    return () => {
      created.stop()
      if (sync.current === created) sync.current = null
    }
  }, [boardId, setNodes, setEdges])

  // Jede Änderung der Zeichenfläche melden. Ob und wann gespeichert wird, entscheidet der Abgleich.
  useEffect(() => { sync.current?.edit({ nodes, edges }) }, [nodes, edges])

  const actions = useMemo<BoardActions>(() => ({
    retry: () => sync.current?.retry() ?? Promise.resolve(),
    keepMine: () => sync.current?.keepMine() ?? Promise.resolve(),
    takeTheirs: () => sync.current?.takeTheirs() ?? Promise.resolve(),
    apply: (action) => sync.current?.apply(action) ?? Promise.resolve(false),
    adopt: (next) => sync.current?.adopt(next),
    poll: () => sync.current?.poll() ?? Promise.resolve(),
  }), [])

  const onConnect = useCallback((c: Connection) => {
    setEdges((es) => addEdge({ ...c, animated: true, style: { stroke: "#818cf8", strokeWidth: 2 } }, es))
  }, [setEdges])

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    const raw = event.dataTransfer.getData("application/blueprint-node")
    if (!raw) return
    const { subtype } = JSON.parse(raw) as { subtype: string }
    const kind = kindOf(subtype)
    const position = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const node: BPNode = {
      id: genId(subtype),
      type: nodeTypeFor(kind),
      position,
      data: {
        kind, subtype, label: labelOf(subtype), note: "",
        ...(hasPlaceholder(subtype) ? { placeholder: "" } : {}),
      },
    }
    setNodes((ns) => [...ns, node])
  }, [rf, setNodes])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
  }, [])

  const onNodeClick = useCallback((_: React.MouseEvent, n: BPNode) => setSelectedId(n.id), [])
  const onPaneClick = useCallback(() => setSelectedId(null), [])

  const selectedNode = nodes.find((n) => n.id === selectedId)

  const updateNodeData = (patch: Partial<BPNode["data"]>) => {
    if (!selectedId) return
    setNodes((ns) => ns.map((n) =>
      n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n) as BPNode[])
  }

  const deleteSelected = () => {
    if (!selectedId) return
    setNodes((ns) => (ns as BPNode[]).filter((n) => n.id !== selectedId))
    setEdges((es) => es.filter((e) => e.source !== selectedId && e.target !== selectedId))
    setSelectedId(null)
  }

  return {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    onDrop, onDragOver, onNodeClick, onPaneClick,
    selectedNode, updateNodeData, deleteSelected,
    status, board, editable: EDITABLE.includes(status), actions,
  }
}
