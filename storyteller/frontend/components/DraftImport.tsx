// Hinweis „N Bücher aus dem Entwurf übernehmen“ (Spec 1b §7). Jedes Buch wird einzeln im Projekt
// angelegt; aus dem Browser gelöscht wird nur, was der Server bestätigt hat.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Upload } from "lucide-react"
import { storyApi } from "../api"
import { draftStore } from "../draftStore"
import { toImport } from "../serverBook"

export function DraftImport({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const { t } = useTranslation("storyteller")
  const [drafts, setDrafts] = useState(() => draftStore.list(projectId))
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string[]>([])
  if (drafts.length === 0) return null

  const takeOver = async () => {
    setBusy(true)
    const done: string[] = []
    const errors: string[] = []
    for (const b of drafts) {
      try {
        await storyApi.importBook(projectId, toImport(b))
        done.push(b.id)
      } catch (e) {
        errors.push(`${b.title}: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    if (done.length && !draftStore.forget(projectId, done)) errors.push(t("draft_forget_failed"))
    setDrafts(draftStore.list(projectId))
    setFailed(errors)
    setBusy(false)
    onDone()
  }

  return (
    <div className="st-draft-import space-y-2 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-amber-100">{t("draft_found", { count: drafts.length })}</p>
        <button onClick={() => { void takeOver() }} disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-semibold text-zinc-950 hover:bg-amber-400 disabled:opacity-50">
          <Upload className="h-4 w-4" />{t("draft_take_over", { count: drafts.length })}
        </button>
      </div>
      <p className="text-xs text-amber-200/70">{drafts.map((b) => b.title).join(" · ")}</p>
      {failed.map((f) => <p key={f} className="text-xs text-red-300">{f}</p>)}
    </div>
  )
}
