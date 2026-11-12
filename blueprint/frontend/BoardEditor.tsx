import { useState } from "react"
import { ReactFlowProvider, useEdgesState, useNodesState } from "@xyflow/react"
import { Copy, History, MessagesSquare } from "lucide-react"
import { AgentDock } from "./AgentDock"
import { blueprintApi } from "./api"
import { previewNodes } from "./boardGraph"
import { boardText } from "./boardText"
import { loadDock, saveDock, type DockState } from "./dock"
import { errorText } from "./boardView"
import { useBoard } from "./useBoard"
import { useProposal, useVersions } from "./useProposal"
import { NodePalette } from "./NodePalette"
import { Canvas } from "./Canvas"
import { PropertiesPanel } from "./PropertiesPanel"
import { ProposalBanner } from "./ProposalBanner"
import { SyncNotice } from "./SyncNotice"
import { VersionList } from "./VersionList"
import { BUTTON, BUTTON_ON, ERROR_BOX, RAND, SELECT } from "./styles"
import type { T } from "./texts.de"
import type { Board, Graph, ProjectRef, SyncStatus } from "./types"

interface Props {
  boardId: number
  boardName: string
  projects: ProjectRef[]
  locale: string
  t: T
  /** Stand des offenen Boards für die Liste (Name, Projekt, offener Vorschlag). */
  onBoard: (board: Board) => void
}

const TROUBLE: readonly SyncStatus[] = ["save_error", "conflict", "load_error", "unreadable", "gone"]

/** Der Vorschlag zum Ansehen: eigene Zeichenfläche mit eigenem Zustand, die Fassung des Nutzers bleibt unberührt. */
function PreviewCanvas({ graph, freshIds, t }: { graph: Graph; freshIds: ReadonlySet<string>; t: T }) {
  const [nodes, , onNodesChange] = useNodesState(previewNodes(graph.nodes, freshIds))
  const [edges, , onEdgesChange] = useEdgesState(graph.edges)
  return <Canvas nodes={nodes} edges={edges} readOnly t={t} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} />
}

function EditorInner({ boardId, boardName, projects, locale, t, onBoard }: Props) {
  const b = useBoard(boardId, onBoard)
  const proposal = useProposal(b.board, b.nodes, b.edges, b.actions, t)
  const [showVersions, setShowVersions] = useState(false)
  const versions = useVersions(boardId, showVersions, b.board?.revision, b.actions, t)
  const [copied, setCopied] = useState<"" | "ok" | "fail">("")
  const [projectError, setProjectError] = useState<string | null>(null)
  const [dock, setDockState] = useState<DockState>(loadDock)
  const setDock = (next: DockState) => { setDockState(next); saveDock(next) }
  const shown = proposal.preview && proposal.graph ? proposal.graph : { nodes: b.nodes, edges: b.edges }
  const projectId = b.board?.project_id ?? null
  const projectKnown = projectId === null || projects.some((item) => item.id === projectId)

  // Das Gezeigte als Text in die Zwischenablage — gleicher Text wie das Agent-Tool blueprint_read.
  async function copyAsText() {
    try {
      await navigator.clipboard.writeText(boardText(boardName, shown.nodes, shown.edges))
      setCopied("ok")
    } catch {
      setCopied("fail")
    }
    setTimeout(() => setCopied(""), 2000)
  }

  async function changeProject(next: string | null) {
    setProjectError(null)
    try {
      b.actions.adopt(await blueprintApi.update(boardId, { project_id: next }))
    } catch (problem) {
      setProjectError(errorText(problem, t))
    }
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className={`flex flex-wrap items-center gap-x-3 gap-y-2 border-b ${RAND} px-4 py-2.5`}>
          <span className="truncate text-sm font-medium text-[#e8eef8]">{boardName}</span>
          <span role="status" className={`text-xs ${TROUBLE.includes(b.status) ? "text-rose-200" : "text-[#9aa7bc]"}`}>
            {t(`status_${b.status}`)}
          </span>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {b.board && (projects.length > 0 || projectId !== null) && (
              <select value={projectId ?? ""} onChange={(e) => void changeProject(e.target.value || null)}
                aria-label={t("project_label")} title={t("project_label")} className={`${SELECT} w-auto max-w-[14rem]`}>
                <option value="">{t("no_project")}</option>
                {!projectKnown && <option value={projectId ?? ""}>{t("unknown_project")}</option>}
                {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            )}
            <button type="button" onClick={() => setShowVersions((open) => !open)} aria-pressed={showVersions}
              className={showVersions ? BUTTON_ON : BUTTON}>
              <History size={13} aria-hidden />{t("versions_title")}
            </button>
            <button type="button" onClick={() => setDock({ ...dock, open: !dock.open })} aria-pressed={dock.open}
              title={t("chat_title")} className={dock.open ? BUTTON_ON : BUTTON}>
              <MessagesSquare size={13} aria-hidden />{t("chat_open")}
            </button>
            <button type="button" onClick={() => void copyAsText()} title={t("copy_hint")} className={BUTTON}>
              <Copy size={13} aria-hidden />
              {copied === "ok" ? t("copied") : copied === "fail" ? t("copy_failed") : t("copy")}
            </button>
          </div>
        </div>
        <SyncNotice status={b.status} busy={false} t={t} onRetry={() => void b.actions.retry()}
          onKeepMine={() => void b.actions.keepMine()} onTakeTheirs={() => void b.actions.takeTheirs()} />
        {projectError && <p role="alert" className={`${ERROR_BOX} m-2`}>{projectError}</p>}
        {proposal.open && (
          <ProposalBanner note={b.board?.proposal_note ?? null} at={b.board?.proposal_at ?? null} diff={proposal.diff}
            preview={proposal.preview} busy={proposal.busy} error={proposal.error} locale={locale} t={t}
            onPreview={proposal.togglePreview} onAccept={() => void proposal.accept()}
            onDiscard={() => void proposal.discard()} />
        )}
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <NodePalette disabled={!b.editable || proposal.preview} />
          {proposal.preview && proposal.graph && proposal.diff ? (
            <ReactFlowProvider key={b.board?.proposal_at ?? "vorschau"}>
              <PreviewCanvas graph={proposal.graph} freshIds={proposal.diff.freshIds} t={t} />
            </ReactFlowProvider>
          ) : (
            <Canvas nodes={b.nodes} edges={b.edges} readOnly={!b.editable} t={t}
              onNodesChange={b.onNodesChange} onEdgesChange={b.onEdgesChange} onConnect={b.onConnect}
              onNodeClick={b.onNodeClick} onPaneClick={b.onPaneClick} onDrop={b.onDrop} onDragOver={b.onDragOver} />
          )}
          {showVersions ? (
            <VersionList versions={versions.versions} error={versions.loadFailed} message={versions.message}
              busy={versions.busy} locale={locale} t={t} onRestore={(id) => void versions.restore(id)}
              onClose={() => setShowVersions(false)} />
          ) : (!dock.open || (b.selectedNode && !proposal.preview)) && (
            <PropertiesPanel node={b.selectedNode} preview={proposal.preview} t={t}
              onChange={b.updateNodeData} onDelete={b.deleteSelected} />
          )}
        </div>
      </div>
      {dock.open && b.board && (
        <AgentDock key={`${boardId}:${projectId ?? ""}`} boardId={boardId} projectId={projectId} width={dock.width}
          t={t} onWidth={(width) => setDock({ open: true, width })} onClose={() => setDock({ ...dock, open: false })} />
      )}
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
