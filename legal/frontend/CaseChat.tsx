import { useEffect, useState } from "react"
import { Loader2, X } from "lucide-react"
import { ChatPane } from "@/features/chat/ChatPane"
import { caseApi } from "./api"
import { errorText } from "./caseFormat"

/** Chat mit dem Rechts-Agenten neben der Fallakte (Muster: Storyteller ChatDock). Sitzung je Fall wird weiterverwendet;
 * metadata.embedded_in sorgt dafür, dass das Projekt-Cockpit sie nicht von selbst öffnet. */
export function CaseChat({ pid, onClose }: { pid: string; onClose: () => void }) {
  const [session, setSession] = useState<{ session_id: string; agent_id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { caseApi.chat(pid).then(setSession).catch((e) => setError(errorText(e))) }, [pid])

  return (
    <aside className="flex w-[min(560px,45vw)] shrink-0 flex-col rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_29))]">
      <div className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8]">
        <span className="flex-1">Rechts-Agent</span>
        <button type="button" onClick={onClose} title="Schließen" className="rounded p-1 text-[#9aa7bc] hover:bg-white/10"><X size={14} /></button>
      </div>
      <p className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-[11px] leading-4 text-amber-200/80">
        Keine Rechtsberatung. Der Agent zitiert Normen aus dem Korpus und legt Vorschläge ab – übernehmen musst du selbst.
      </p>
      <div className="min-h-0 flex-1">
        {error && <p className="m-3 text-xs text-rose-300">{error}</p>}
        {session ? (
          <ChatPane key={session.session_id} deepLinkSid={session.session_id} projectId={pid} showSidePanels={false}
            preferredAgentId={session.agent_id} agentSelectionExplicit />
        ) : !error && (
          <div className="flex h-full items-center justify-center text-sm text-[#9aa7bc]"><Loader2 size={14} className="mr-2 animate-spin" />Chat wird geöffnet …</div>
        )}
      </div>
    </aside>
  )
}
