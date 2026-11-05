import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { BTN } from "./ui"

/** Zeitmaschine in einfacher Form: Liste der gespeicherten Schritte, je Schritt ein Knopf „Hierhin zurück“. */
export function History({ projectId }: { projectId: string }) {
  const { t } = useTranslation("vibe")
  const [items, setItems] = useState<api.VibeVersion[] | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => api.getVersions(projectId).then((r) => setItems(r.versions)).catch(() => setItems([])), [projectId])
  useEffect(() => { void load(); const id = setInterval(() => void load(), 5000); return () => clearInterval(id) }, [load])

  const back = async (sha: string) => {
    setBusy(true); setNote(null)
    try { await api.restoreVersion(projectId, sha); setNote(t("restored")); await load() }
    catch { setNote(t("err.general")) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-[#e8eef8]">{t("history")}</h3>
      <p className="text-xs text-[#9aa7bc]">{t("history_hint")}</p>
      {note && <p className="text-sm text-emerald-300" aria-live="polite">{note}</p>}
      {items && items.length === 0 && <p className="text-sm text-[#c8d2df]">{t("no_versions")}</p>}
      <ul className="space-y-1">
        {(items ?? []).map((v, i) => (
          <li key={v.commit_id} className="flex items-center gap-2 text-sm text-[#c8d2df]">
            <span className="flex-1 truncate">{v.summary || "…"}</span>
            {i > 0 && <button type="button" className={BTN} disabled={busy} onClick={() => void back(v.commit_id)}>{t("go_back")}</button>}
          </li>
        ))}
      </ul>
    </div>
  )
}
