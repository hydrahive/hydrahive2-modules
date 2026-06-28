import React, { useCallback, useEffect, useRef, useState } from "react"
import {
  addEdge, useEdgesState, useNodesState, useReactFlow,
  type Connection, type Edge,
} from "@xyflow/react"
import { blueprintApi } from "./api"
import { kindOf, labelOf, hasPlaceholder } from "./palette-data"
import { nodeTypeFor } from "./nodes"
import type { BPNode } from "./types"

let _seq = 0
const genId = (s: string) => `${s}-${++_seq}-${Date.now()}`

export function useBoard(boardId: number | null) {
  const [nodes, setNodes, onNodesChange] = useNodesState<BPNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saved, setSaved] = useState(true)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const rf = useReactFlow()

  // Board laden
  useEffect(() => {
    if (boardId == null) { setNodes([]); setEdges([]); return }
    blueprintApi.get(boardId).then((b) => {
      try {
        const g = JSON.parse(b.graph_json) as { nodes: BPNode[]; edges: Edge[] }
        setNodes(g.nodes ?? [])
        setEdges(g.edges ?? [])
      } catch { setNodes([]); setEdges([]) }
      setSelectedId(null)
      setSaved(true)
    }).catch(() => {})
  }, [boardId, setNodes, setEdges])

  // Debounced Auto-Save
  const scheduleSave = useCallback((ns: BPNode[], es: Edge[]) => {
    if (boardId == null) return
    setSaved(false)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const graph_json = JSON.stringify({ nodes: ns, edges: es })
      blueprintApi.update(boardId, { graph_json }).then(() => setSaved(true)).catch(() => {})
    }, 700)
  }, [boardId])

  useEffect(() => { scheduleSave(nodes, edges) }, [nodes, edges, scheduleSave])

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
    selectedNode, updateNodeData, deleteSelected, saved,
  }
}
