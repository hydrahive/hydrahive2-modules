import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowLeft, Download, RotateCcw, Trash2 } from "lucide-react"
import { ModuleViewFrame } from "@/features/chat/ModuleViewFrame"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { download, getVersions, purge, restore, toTrash, type Item, type Version } from "./api"
import { errorKey, kindLabelKey, sameUser, shortDate } from "./logic"
import { PurgeDialog } from "./PurgeDialog"

interface Props { item: Item; onBack: () => void; onChanged: () => void }

/** Ein Diagramm groß ansehen (abgeschotteter Rahmen aus dem Kern), Fassungen, Herunterladen, Papierkorb. */
export function Viewer({ item, onBack, onChanged }: Props) {
  const { t } = useTranslation("diagramme")
  const username = useAuthStore((s: { username?: string | null }) => s.username)
  const role = useAuthStore((s: { role?: string | null }) => s.role)
  const [shown, setShown] = useState(item.id)
  const [versions, setVersions] = useState<Version[]>([])
  const [ask, setAsk] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState("")
  const mayChange = sameUser(item, username, role)
  const inTrash = !!item.deleted_at

  useEffect(() => { getVersions(item.id).then(setVersions).catch(() => {}) }, [item.id])

  const act = async (fn: () => Promise<unknown>, back = true) => {
    setBusy(true); setMsg("")
    try { await fn(); onChanged(); if (back) onBack() } catch (e) { setMsg(t(errorKey(e))) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3" data-diagram-viewer>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={onBack} className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-100">
          <ArrowLeft size={14} />{t("back_to_list")}
        </button>
        <span className="flex-1" />
        <button type="button" onClick={() => download(shown, item.title).catch((e) => setMsg(t(errorKey(e))))}
          className="flex items-center gap-1 rounded px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5"><Download size={14} />{t("download")}</button>
        {mayChange && !inTrash && (
          <button type="button" disabled={busy} onClick={() => act(() => toTrash(item.id))}
            className="flex items-center gap-1 rounded px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5"><Trash2 size={14} />{t("to_trash")}</button>
        )}
        {mayChange && inTrash && (<>
          <button type="button" disabled={busy} onClick={() => act(() => restore(item.id))}
            className="flex items-center gap-1 rounded px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5"><RotateCcw size={14} />{t("restore")}</button>
          <button type="button" disabled={busy} onClick={() => setAsk(true)}
            className="flex items-center gap-1 rounded px-3 py-1.5 text-sm text-rose-300 hover:bg-rose-500/10"><Trash2 size={14} />{t("purge")}</button>
        </>)}
      </div>
      {msg && <p className="text-sm text-rose-300">{msg}</p>}
      <div className="text-xs text-zinc-400">{t(kindLabelKey(item.kind))}{item.project_name ? ` · ${item.project_name}` : ""} · {shortDate(item.created_at)}</div>
      <ModuleViewFrame key={shown} module="diagramme" viewId={shown} title={item.title} />
      {versions.length > 1 && (
        <section className="space-y-1">
          <h3 className="text-xs font-semibold text-zinc-300">{t("versions")}</h3>
          <ul className="flex flex-wrap gap-2">
            {[...versions].reverse().map((v, i) => (
              <li key={v.id}>
                <button type="button" onClick={() => setShown(v.id)} aria-pressed={shown === v.id}
                  className={`rounded border px-2 py-1 text-xs ${shown === v.id ? "border-sky-400 text-sky-200" : "border-white/10 text-zinc-400 hover:text-zinc-100"}`}>
                  {shortDate(v.created_at)}{i === 0 ? ` (${t("version_current")})` : ""}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {ask && <PurgeDialog title={item.title} busy={busy} onClose={() => setAsk(false)}
        onConfirm={() => act(async () => { await purge(item.id); setAsk(false) })} />}
    </div>
  )
}
