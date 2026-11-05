import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ChatPane } from "@/features/chat/ChatPane"
import * as api from "./api"
import { History } from "./History"
import { BTN } from "./ui"

/** Ein geöffnetes Projekt: links der Chat mit dem Agenten, rechts die Ansicht und die Versionen („Zurück“). */
export function Workspace({ project, onBack }: { project: api.VibeProject; onBack: () => void }) {
  const { t } = useTranslation("vibe")
  const [session, setSession] = useState<{ session_id: string; agent_id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    setSession(null); setError(null)
    api.openChat(project.project_id).then(setSession).catch((e) => setError(api.errorKey(e, ["vibe_container_down", "vibe_not_ready", "vibe_project_not_found"])))
  }, [project.project_id])

  return (
    <div className="flex h-[calc(100vh-4rem)] min-h-[480px] flex-col gap-2 p-3">
      <div className="flex items-center gap-3">
        <button type="button" className={BTN} onClick={onBack}>← {t("back")}</button>
        <h1 className="truncate text-lg font-semibold text-[#e8eef8]">{project.name}</h1>
      </div>
      <div className="flex min-h-0 flex-1 gap-3">
        <section className="flex w-[min(560px,45vw)] shrink-0 flex-col rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_29))]">
          <h2 className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8]">{t("chat_title")}</h2>
          <div className="min-h-0 flex-1">
            {error && <p className="m-3 text-sm text-rose-300" role="alert">{t(error)}</p>}
            {session ? (
              <ChatPane key={session.session_id} deepLinkSid={session.session_id} projectId={project.project_id} showSidePanels={false}
                preferredAgentId={session.agent_id} agentSelectionExplicit />
            ) : !error && (
              <div className="flex h-full items-center justify-center text-sm text-[#9aa7bc]"><Loader2 size={14} className="mr-2 animate-spin" />…</div>
            )}
          </div>
        </section>
        <section className="flex min-w-0 flex-1 flex-col gap-3 overflow-auto rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_29))] p-3">
          <h2 className="text-sm text-[#e8eef8]">{t("preview_title")}</h2>
          <p className="text-sm text-[#c8d2df]">{t("preview_none")}</p>
          <History projectId={project.project_id} />
        </section>
      </div>
    </div>
  )
}
