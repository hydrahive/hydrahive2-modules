// Versionskonflikt (Spec 1b §3): Jemand anderes (anderes Fenster, Agent) hat inzwischen gespeichert.
// Zwei Wege, beide ohne Verlust: neu laden (eigene Fassung → Schnappschuss) oder eigene behalten
// (fremde Fassung → Schnappschuss). Bis zur Entscheidung wird nichts gespeichert.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { AlertTriangle } from "lucide-react"
import type { Conflict } from "../useBook"

interface Props { conflict: Conflict; onResolve: (how: "reload" | "keep") => Promise<void> }

export function ConflictDialog({ conflict, onResolve }: Props) {
  const { t } = useTranslation("storyteller")
  const [busy, setBusy] = useState(false)
  const what = conflict.kind === "scene" ? t("conflict_scene", { title: conflict.title })
    : conflict.kind === "structure" ? t("conflict_structure") : t("conflict_book")
  const pick = async (how: "reload" | "keep") => {
    setBusy(true)
    try { await onResolve(how) } finally { setBusy(false) }
  }
  return (
    <div className="st-conflict fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="alertdialog" aria-modal="true" aria-labelledby="st-conflict-title">
      <div className="w-full max-w-md space-y-4 rounded-2xl border border-amber-400/30 bg-zinc-900 p-6 shadow-2xl">
        <h2 id="st-conflict-title" className="flex items-center gap-2 text-lg font-bold text-amber-200">
          <AlertTriangle className="h-5 w-5" />{t("conflict_title")}
        </h2>
        <p className="text-sm text-zinc-300">{what} {t("conflict_by")}</p>
        <p className="text-xs text-zinc-500">{conflict.kind === "scene" ? t("conflict_safe_scene") : t("conflict_safe_other")}</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button disabled={busy} onClick={() => { void pick("reload") }}
            className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-200 hover:bg-white/5 disabled:opacity-50">{t("conflict_reload")}</button>
          <button disabled={busy} onClick={() => { void pick("keep") }}
            className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{t("conflict_keep")}</button>
        </div>
      </div>
    </div>
  )
}
