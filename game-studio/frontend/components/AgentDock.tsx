// Chat mit dem Projektagenten, rechts neben der Arbeitsfläche (Vorbild: Storyteller ChatDock).
import { Loader2, MessagesSquare, X } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ChatPane } from "@/features/chat/ChatPane"
import { gameStudioApi } from "../api"
import { clampWidth } from "../dock"
import type { ChatInfo } from "../types"

interface Props { projectId: string; width: number; onWidth: (width: number) => void; onClose: () => void }

export function AgentDock({ projectId, width, onWidth, onClose }: Props) {
  const { t } = useTranslation("gameStudio")
  const [info, setInfo] = useState<ChatInfo | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    gameStudioApi.chatInfo(projectId)
      .then(async (result) => {
        if (cancelled) return
        setInfo(result)
        if (result.agent && result.can_start) {
          const started = await gameStudioApi.startChat(projectId)
          if (!cancelled) setSessionId(started.session_id)
        }
      })
      .catch(() => { if (!cancelled) setError(true) })
    return () => { cancelled = true }
  }, [projectId])

  const drag = (event: React.PointerEvent<HTMLDivElement>) => {
    const startX = event.clientX
    const startWidth = width
    const move = (e: PointerEvent) => onWidth(clampWidth(startWidth + (startX - e.clientX), window.innerWidth))
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up) }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  return (
    <aside className="relative flex shrink-0 flex-col border-l border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))]" style={{ width }}>
      <div onPointerDown={drag} role="separator" aria-orientation="vertical" aria-label={t("workspace.agent.resize")}
        className="absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize hover:bg-[#69d7ff]/30" />
      <div className="flex shrink-0 items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8]">
        <MessagesSquare className="h-4 w-4 text-[#69d7ff]" aria-hidden="true" />
        <span className="flex-1 truncate">{info?.agent ? info.agent.name : t("workspace.agent.title")}</span>
        <button type="button" onClick={onClose} title={t("workspace.agent.close")} className="rounded p-1 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"><X className="h-4 w-4" aria-hidden="true" /></button>
      </div>
      {error && <p role="alert" className="m-3 text-xs text-red-300">{t("workspace.agent.failed")}</p>}
      {info && !info.agent && <p className="m-3 rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">{t("workspace.agent.noAgent")}</p>}
      {info?.agent && !info.can_start && <p className="m-3 text-xs text-[#c8d2df]">{t("workspace.agent.readOnly")}</p>}
      <div className="min-h-0 flex-1 [&_h2]:whitespace-normal [&_div:has(>h2)]:min-w-[12rem] [&_div:has(>div>h2)]:flex-wrap [&_div:has(>div>h2)>div:last-child]:shrink [&_div:has(>div>h2)>div:last-child]:flex-wrap">
        {sessionId && info?.agent ? (
          <ChatPane key={sessionId} deepLinkSid={sessionId} projectId={projectId} showSidePanels={false}
            preferredAgentId={info.agent.id} agentSelectionExplicit />
        ) : !error && info?.can_start !== false && (
          <div className="flex h-full items-center justify-center text-sm text-[#9aa7bc]"><Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />{t("workspace.agent.loading")}</div>
        )}
      </div>
    </aside>
  )
}
