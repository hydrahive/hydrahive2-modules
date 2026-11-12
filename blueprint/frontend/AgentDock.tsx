// Chat mit dem Projekt-Agenten rechts neben dem Board (Vorbild: Game Studio AgentDock, Storyteller ChatDock).
// Eingebettet ist die Chatansicht des Kerns mit der Sitzung dieses Boards (dieselbe je Board, der Verlauf bleibt).
import { Loader2, MessagesSquare, X } from "lucide-react"
import { useEffect, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { ChatPane } from "@/features/chat/ChatPane"
import { blueprintApi } from "./api"
import { errorText } from "./boardView"
import { ChatNotice } from "./ChatNotice"
import { addMissingTools, clampWidth, openChat } from "./dock"
import { RAND } from "./styles"
import type { T } from "./texts.de"
import type { ChatInfo, ChatStart } from "./types"

interface Props {
  boardId: number
  /** Projekt des Boards. Der Editor setzt je Board und Projekt einen eigenen key: Der Zustand beginnt dann neu. */
  projectId: string | null
  width: number
  t: T
  onWidth: (width: number) => void
  onClose: () => void
}

// Die Chatansicht ist für breite Flächen gebaut: Im schmalen Dock darf ihr Kopf umbrechen.
const PANE = "min-h-0 flex-1 [&_h2]:whitespace-normal [&_div:has(>h2)]:min-w-[12rem] [&_div:has(>div>h2)]:flex-wrap " +
  "[&_div:has(>div>h2)>div:last-child]:shrink [&_div:has(>div>h2)>div:last-child]:flex-wrap"

export function AgentDock({ boardId, projectId, width, t, onWidth, onClose }: Props) {
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [info, setInfo] = useState<ChatInfo | null>(null)
  const [started, setStarted] = useState<ChatStart | null>(null)
  const [failed, setFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [toolsError, setToolsError] = useState<string | null>(null)
  const [showIntro, setShowIntro] = useState(false)
  const [copied, setCopied] = useState<"" | "ok" | "fail">("")

  useEffect(() => {
    let cancelled = false
    openChat(boardId, blueprintApi, (early) => { if (!cancelled) setInfo(early) })
      .then((opening) => {
        if (cancelled) return
        setStarted(opening.started)
        setShowIntro(opening.showIntro)
      })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => { cancelled = true }
  }, [boardId])

  async function addTools() {
    if (!info) return
    setBusy(true)
    setToolsError(null)
    const result = await addMissingTools(boardId, info, blueprintApi, (problem) => errorText(problem, t))
    setInfo(result.info)
    setToolsError(result.toolsError)
    setBusy(false)
  }

  async function copyIntro() {
    try {
      await navigator.clipboard.writeText(started?.intro ?? "")
      setCopied("ok")
    } catch {
      setCopied("fail")
    }
    setTimeout(() => setCopied(""), 2000)
  }

  const drag = (event: React.PointerEvent<HTMLDivElement>) => {
    const startX = event.clientX
    const startWidth = width
    const move = (e: PointerEvent) => onWidth(clampWidth(startWidth + (startX - e.clientX), window.innerWidth))
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up) }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  const waiting = !failed && started === null && (info === null || info.can_start)
  return (
    <aside aria-label={t("chat_title")} style={{ width }}
      className={`relative flex shrink-0 flex-col border-l ${RAND} bg-[rgb(var(--hh-s-box,21_28_43))]`}>
      <div onPointerDown={drag} role="separator" aria-orientation="vertical" aria-label={t("chat_resize")}
        className="absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize hover:bg-[#69d7ff]/30" />
      <div className={`flex shrink-0 items-center gap-2 border-b ${RAND} px-3 py-1.5 text-sm text-[#e8eef8]`}>
        <MessagesSquare size={15} className="shrink-0 text-[#69d7ff]" aria-hidden />
        <span className="flex-1 truncate">{info?.agent?.name ?? t("chat_title")}</span>
        <button type="button" onClick={onClose} title={t("chat_close")} aria-label={t("chat_close")}
          className="rounded p-1 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">
          <X size={15} aria-hidden />
        </button>
      </div>
      <ChatNotice info={info} intro={started?.intro ?? null} showIntro={showIntro} isAdmin={isAdmin} busy={busy}
        failed={failed} toolsError={toolsError} copied={copied} t={t} onAddTools={() => void addTools()}
        onCopy={() => void copyIntro()} onToggleIntro={() => setShowIntro((shown) => !shown)} />
      <div className={PANE}>
        {started && info?.agent && projectId ? (
          <ChatPane key={started.session_id} deepLinkSid={started.session_id} projectId={projectId}
            showSidePanels={false} preferredAgentId={info.agent.id} agentSelectionExplicit />
        ) : waiting && (
          <div className="flex h-full items-center justify-center text-sm text-[#9aa7bc]">
            <Loader2 size={15} className="mr-2 animate-spin" aria-hidden />{t("chat_loading")}
          </div>
        )}
      </div>
    </aside>
  )
}
