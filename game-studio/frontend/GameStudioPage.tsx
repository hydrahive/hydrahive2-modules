import { AlertTriangle, LoaderCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { gameStudioApi } from "./api"
import { GuidedFlow } from "./GuidedFlow"
import { LandingPage } from "./LandingPage"
import type { DraftCreate, DraftPatch, EntryKind, GameDraft, GameStudioOverview } from "./types"

export function GameStudioPage() {
  const { t } = useTranslation("gameStudio")
  const [overview, setOverview] = useState<GameStudioOverview | null>(null)
  const [kind, setKind] = useState<EntryKind | null>(null)
  const [draft, setDraft] = useState<GameDraft | null>(null)
  const [error, setError] = useState(false)

  const reload = () => {
    setError(false)
    gameStudioApi.overview().then(setOverview).catch(() => setError(true))
  }

  useEffect(() => { reload() }, [])

  const start = (entryKind: EntryKind) => {
    setKind(entryKind)
    setDraft(null)
  }

  const open = (selected: GameDraft) => {
    setKind(selected.entry_kind)
    setDraft(selected)
  }

  const create = async (body: DraftCreate) => {
    const created = await gameStudioApi.createDraft(body)
    setDraft(created)
    setOverview((current) => current ? { ...current, drafts: [created, ...current.drafts] } : current)
    return created
  }

  const update = async (currentDraft: GameDraft, patch: DraftPatch) => {
    const updated = await gameStudioApi.updateDraft(currentDraft.draft_id, patch)
    setDraft(updated)
    setOverview((current) => current ? {
      ...current,
      drafts: current.drafts.map((item) => item.draft_id === updated.draft_id ? updated : item),
    } : current)
    return updated
  }

  const back = () => {
    setKind(null)
    setDraft(null)
    reload()
  }

  if (error) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-xl items-center justify-center px-5 text-center">
        <div><AlertTriangle className="mx-auto text-amber-300" aria-hidden="true" /><h1 className="mt-3 text-lg font-semibold text-[#e8eef8]">{t("error.title")}</h1><p className="mt-1 text-sm text-[#9aa7bc]">{t("error.text")}</p><button type="button" onClick={reload} className="mt-4 rounded-lg bg-[#69d7ff] px-4 py-2 text-sm font-semibold text-[#0d1420]">{t("error.retry")}</button></div>
      </main>
    )
  }

  if (!overview) {
    return <div className="flex min-h-[60vh] items-center justify-center"><LoaderCircle className="animate-spin text-[#69d7ff]" aria-label={t("loading")} /></div>
  }

  if (kind) {
    return <GuidedFlow kind={kind} draft={draft} onBack={back} onCreate={create} onUpdate={update} />
  }

  return <LandingPage drafts={overview.drafts} workstation={overview.workstation} onStart={start} onOpen={open} />
}
