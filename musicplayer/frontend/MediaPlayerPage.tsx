import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { buddyApi } from "@/features/buddy/api"
import { MusicPlayerProjectView } from "./MusicPlayerProjectView"

export function MediaPlayerPage() {
  const { t } = useTranslation("musicplayer"); const [projectId, setProjectId] = useState<string | null>(null); const [loading, setLoading] = useState(true)
  useEffect(() => { buddyApi.state().then((state) => setProjectId(state.project_id)).catch(() => setProjectId(null)).finally(() => setLoading(false)) }, [])
  return <CockpitShell title={t("mp_title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader><CockpitTopbar active="/musicplayer" context={t("mp_title")} /><main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6"><div className="mx-auto max-w-6xl">{loading ? <div className="h-48 animate-pulse rounded-[4px] bg-[#151c2b]" /> : projectId ? <MusicPlayerProjectView projectId={projectId} large /> : <p className="rounded-[4px] border border-dashed border-[#2a364b] bg-[#0d1420] p-6 text-center text-sm text-[#8d9ab0]">{t("mp_select_project")}</p>}</div></main></CockpitShell>
}
