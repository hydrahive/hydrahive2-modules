// Ghostwriter G4e – Chat-Fenster im Storyteller (Spec §11.5): die Kern-Chatansicht (ChatPane, wie im Projekt-
// Cockpit) rechts neben dem Editor, mit der Storyteller-Sitzung dieses Buchs (dieselbe je Buch, Verlauf bleibt).
// Vorschläge des Agenten erscheinen wie gewohnt im Buch; solange das Fenster offen ist, wird nachgefragt.
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, MessagesSquare, Wrench, X } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { ChatPane } from "@/features/chat/ChatPane"
import { clampWidth } from "../chatDock"
import type { BookState } from "../useBook"
import { useChatMode } from "../useChatMode"

interface Props { state: BookState; sceneId: string; width: number; onWidth: (w: number) => void; onClose: () => void }

export function ChatDock({ state, sceneId, width, onWidth, onClose }: Props) {
  const { t } = useTranslation("storyteller")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const chat = useChatMode(state, sceneId)
  const { info, error, busy } = chat
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [request, setRequest] = useState<string | null>(null)
  const opened = useRef(false)

  // Sitzung einmal je geöffnetem Fenster holen (wiederverwendet je Buch), sobald der Agent bekannt ist.
  useEffect(() => {
    if (opened.current || !info?.agent || !info.can_start) return
    opened.current = true
    void chat.openHere().then((s) => { if (s) { setSessionId(s.session_id); setRequest(s.session_id) } })
  }, [info, chat])

  const drag = (e: React.PointerEvent<HTMLDivElement>) => {
    const startX = e.clientX, startW = width
    const move = (ev: PointerEvent) => onWidth(clampWidth(startW + (startX - ev.clientX), window.innerWidth))
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up) }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  return (
    <aside className="st-chat-dock relative flex shrink-0 flex-col border-l border-white/10 bg-[#151c2b]" style={{ width }}>
      <div onPointerDown={drag} role="separator" aria-orientation="vertical" aria-label={t("chat_dock_resize")}
        className="absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize hover:bg-violet-400/30" />
      <div className="flex shrink-0 items-center gap-2 border-b border-white/10 px-3 py-1.5 text-sm text-zinc-200">
        <MessagesSquare className="h-4 w-4 text-violet-300" />
        <span className="flex-1 truncate">{info?.agent ? t("chat_dock_title", { name: info.agent.name }) : t("chat_dock_title_plain")}</span>
        <button onClick={onClose} title={t("chat_dock_close")} className="rounded p-1 text-zinc-400 hover:bg-white/10 hover:text-zinc-100"><X className="h-4 w-4" /></button>
      </div>
      {info && !info.agent && <p className="m-3 rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">{t("chat_no_agent")}</p>}
      {info?.agent && info.tools_missing.length > 0 && (
        <div className="st-chat-tools-missing m-3 space-y-2 rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">
          <p>{t("chat_tools_missing", { tools: info.tools_missing.join(", ") })}</p>
          {isAdmin
            ? <button onClick={() => { void chat.addTools() }} disabled={busy} className="inline-flex items-center gap-1.5 rounded bg-amber-600/80 px-3 py-1 text-white disabled:opacity-40">
                <Wrench className="h-3.5 w-3.5" />{t("chat_add_tools")}
              </button>
            : <p>{t("chat_tools_ask_admin")}</p>}
        </div>
      )}
      {info?.agent && !info.can_start && <p className="m-3 text-xs text-zinc-400">{t("chat_dock_read_only")}</p>}
      {error && <p className="m-3 text-xs text-red-200" role="alert">{t(`ai_err_${error.code}`, { defaultValue: error.message || error.code })}</p>}
      {/* Kopf der Kern-Chatansicht ist für das breite Cockpit gebaut (Knopfleiste ~730 px, schrumpft nicht). Im schmalen
          Fenster darf die Kopfzeile umbrechen: Titel/Modell oben, Knöpfe darunter – statt den Titel zusammenzuquetschen. */}
      <div className="st-chat-dock-body min-h-0 flex-1 [&_h2]:whitespace-normal [&_div:has(>h2)]:min-w-[12rem] [&_div:has(>div>h2)]:flex-wrap [&_div:has(>div>h2)]:py-2">
        {sessionId && info?.agent ? (
          <ChatPane key={sessionId} projectId={state.projectId} showSidePanels={false} preferredAgentId={info.agent.id}
            agentSelectionExplicit openSessionRequest={request} onSessionRequestHandled={() => setRequest(null)} />
        ) : (info?.can_start !== false && !error) && (
          <div className="flex h-full items-center justify-center text-sm text-zinc-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t("chat_dock_loading")}</div>
        )}
      </div>
    </aside>
  )
}
