// KI-Modus „Im Chat“ (Ghostwriter G4a, Spec §11.3): Chat mit dem Projekt-Agenten öffnen. Der Agent liest das Buch
// und legt Szenentext als Vorschlag ab; der erscheint hier wie ein Lauf-Vorschlag (Hinweis über dem Editor).
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, Copy, ExternalLink, Loader2, MessagesSquare, Wrench } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Scene } from "../model"
import type { BookState } from "../useBook"
import { useChatMode } from "../useChatMode"

interface Props { state: BookState; scene: Scene; onGoOutline: () => void; onOpenChat?: () => void }

export function ChatMode({ state, scene, onGoOutline, onOpenChat }: Props) {
  const { t } = useTranslation("storyteller")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const chat = useChatMode(state, scene.id)
  const [copied, setCopied] = useState(false)
  const { info, started, busy, error } = chat
  const btn = "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm disabled:opacity-40"

  const copy = async () => {
    if (!started) return
    try { await navigator.clipboard.writeText(started.intro); setCopied(true) } catch { setCopied(false) }
  }

  return (
    <div className="st-chat-mode space-y-3 text-sm">
      <p className="text-[#c8d2df]">{t("chat_intro")}</p>
      {info && !info.agent && <p className="st-chat-no-agent rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">{t("chat_no_agent")}</p>}
      {info?.agent && <p className="text-xs text-[#c8d2df]">{t("chat_agent", { name: info.agent.name })}</p>}
      {info?.agent && info.tools_missing.length > 0 && (
        <div className="st-chat-tools-missing space-y-2 rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">
          <p>{t("chat_tools_missing", { tools: info.tools_missing.join(", ") })}</p>
          {isAdmin
            ? <button onClick={() => { void chat.addTools() }} disabled={busy} className={`${btn} bg-amber-600/80 text-white`}>
                <Wrench className="h-3.5 w-3.5" />{t("chat_add_tools")}
              </button>
            : <p>{t("chat_tools_ask_admin")}</p>}
        </div>
      )}
      {info?.agent && (
        <div className="flex flex-wrap gap-2">
          {onOpenChat && (
            <button onClick={onOpenChat} disabled={!info.can_start} className={`st-chat-here ${btn} bg-[#163248] font-semibold text-white`}>
              <MessagesSquare className="h-4 w-4" />{t("chat_here")}
            </button>
          )}
          <button onClick={() => { void chat.start() }} disabled={busy || !info.can_start}
            className={`st-chat-start ${btn} ${onOpenChat ? "border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]" : "bg-[#163248] font-semibold text-white"}`}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}{t("chat_start")}
          </button>
        </div>
      )}
      {started && (
        <div className="st-chat-started space-y-2 rounded border border-[#69d7ff]/30 bg-[#69d7ff]/5 p-2">
          <p className="text-xs text-[#c8d2df]">{t("chat_started")}</p>
          <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded bg-black/30 p-2 text-xs text-[#e8eef8]">{started.intro}</pre>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => { void copy() }} className={`st-chat-copy ${btn} border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]`}>
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}{t(copied ? "chat_copied" : "chat_copy")}
            </button>
            <a href={started.url} target="_blank" rel="noreferrer" className={`${btn} border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]`}>
              <ExternalLink className="h-3.5 w-3.5" />{t("chat_open_again")}
            </a>
          </div>
        </div>
      )}
      {state.outlineProposal && (
        <p className="st-chat-outline-hint flex flex-wrap items-center gap-2 rounded border border-[#69d7ff]/30 bg-[#69d7ff]/10 px-2 py-1.5 text-xs text-[#c8f2ff]">
          <span className="flex-1">{t("outline_proposal_hint")}</span>
          <button onClick={onGoOutline} className="rounded px-2 py-0.5 font-semibold hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{t("outline_proposal_go")}</button>
        </p>
      )}
      {state.restructureProposal && (
        <p className="st-chat-restructure-hint flex flex-wrap items-center gap-2 rounded border border-[#69d7ff]/30 bg-[#69d7ff]/10 px-2 py-1.5 text-xs text-[#c8f2ff]">
          <span className="flex-1">{t("struct_proposal_hint")}</span>
          <button onClick={onGoOutline} className="rounded px-2 py-0.5 font-semibold hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{t("outline_proposal_go")}</button>
        </p>
      )}
      <p className="text-xs text-[#9aa7bc]">{t("chat_proposals_hint")}</p>
      {error && <p className="text-xs text-red-200" role="alert">{t(`ai_err_${error.code}`, { defaultValue: error.message || error.code })}</p>}
    </div>
  )
}
