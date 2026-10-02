import { Check, ChevronDown, ChevronRight, Download, FolderInput } from "lucide-react"
import { useCallback, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { filterByKind, groupedSources } from "./mediaUtils"
import type { MediaKind, ProjectSource } from "./types"

export function GeneratedImport({ projectId, kind, onImported }: { projectId: string; kind: MediaKind; onImported: () => void }) {
  const { t } = useTranslation("musicplayer"); const [open, setOpen] = useState(false); const [items, setItems] = useState<ProjectSource[]>([])
  const [loading, setLoading] = useState(false); const [busy, setBusy] = useState<string | null>(null)
  const load = useCallback(() => { setLoading(true); musicApi.listSources(projectId, kind).then((sources) => setItems(filterByKind(sources, kind))).catch(() => setItems([])).finally(() => setLoading(false)) }, [projectId, kind])
  const toggle = () => { const next = !open; setOpen(next); if (next) load() }
  const doImport = async (path: string) => { setBusy(path); try { await musicApi.importSource(projectId, path); onImported(); load() } catch { load() } finally { setBusy(null) } }
  return <div><button type="button" onClick={toggle} aria-expanded={open} className="flex w-full items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-2 text-xs font-bold text-[#c4cedd] hover:border-[#46617f] hover:bg-[#172133]">{open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}<FolderInput size={12} className="text-[#69d7ff]" /><span className="flex-1 text-left">{t("mp_project_sources")}</span></button>{open && <div className="mt-1 max-h-48 space-y-2 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-1">{loading && <p className="px-2 py-1 text-[10px] text-[#8d9ab0]">{t("mp_loading")}</p>}{!loading && items.length === 0 && <p className="px-2 py-1 text-[10px] text-[#8d9ab0]">{t("mp_generated_empty")}</p>}{groupedSources(items).map(([group, sources]) => <section key={group}><p className="px-2 py-1 text-[9px] font-bold uppercase text-[#69d7ff]">{group}</p>{sources.map((item) => <div key={item.path} className="flex items-center gap-2 rounded-[4px] bg-[#111827] px-2 py-1.5"><span className="min-w-0 flex-1 truncate text-[10px] text-[#aab6c8]" title={item.path}>{item.title}</span>{item.already_imported ? <Check size={13} className="text-emerald-400" /> : <button type="button" onClick={() => void doImport(item.path)} disabled={busy === item.path} title={t("mp_import")} aria-label={t("mp_import")} className="text-[#8d9ab0] hover:text-fuchsia-200 disabled:opacity-40"><Download size={13} /></button>}</div>)}</section>)}</div>}</div>
}
