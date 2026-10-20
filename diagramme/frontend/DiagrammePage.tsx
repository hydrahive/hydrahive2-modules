import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { AgentsAccess } from "./AgentsAccess"
import { listItems, type Item } from "./api"
import { errorKey, type Filter } from "./logic"
import { Tile } from "./Tile"
import { Viewer } from "./Viewer"

/** Sammlung aller Diagramme (Spec §12.2): suchen, nach Projekt filtern, ansehen, Papierkorb. */
export function DiagrammePage() {
  const { t } = useTranslation("diagramme")
  const isAdmin = useAuthStore((s: { role?: string | null }) => s.role) === "admin"
  const [filter, setFilter] = useState<Filter>({ q: "", project: "", trash: false })
  const [items, setItems] = useState<Item[] | null>(null)
  const [projects, setProjects] = useState<Record<string, string>>({})
  const [open, setOpen] = useState<Item | null>(null)
  const [msg, setMsg] = useState("")

  const load = useCallback(() => {
    listItems(filter).then((rows) => {
      setItems(rows)
      setMsg("")
      setProjects((old) => {
        const next = { ...old }
        for (const r of rows) if (r.project_id) next[r.project_id] = r.project_name || r.project_id
        return next
      })
    }).catch((e) => setMsg(t(errorKey(e))))
  }, [filter, t])

  useEffect(() => { const h = setTimeout(load, 200); return () => clearTimeout(h) }, [load])

  const projectList = useMemo(() => Object.entries(projects).sort((a, b) => a[1].localeCompare(b[1])), [projects])
  const empty = filter.trash ? "empty_trash" : filter.q || filter.project ? "empty_search" : "empty"

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
        <p className="text-sm text-zinc-400">{t("subtitle")}</p>
      </header>
      {isAdmin && !open && <AgentsAccess />}
      {open ? (
        <Viewer item={open} onBack={() => setOpen(null)} onChanged={load} />
      ) : (<>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex min-w-[240px] flex-1 items-center gap-2 rounded border border-white/10 bg-white/[3%] px-3 py-1.5">
            <Search size={14} className="text-zinc-500" />
            <input value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} aria-label={t("search_placeholder")}
              placeholder={t("search_placeholder")} className="w-full bg-transparent text-sm text-zinc-100 outline-none" />
          </label>
          <select value={filter.project} onChange={(e) => setFilter({ ...filter, project: e.target.value })} aria-label={t("all_projects")}
            className="rounded border border-white/10 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200">
            <option value="">{t("all_projects")}</option>
            <option value="none">{t("no_project")}</option>
            {projectList.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-sm text-zinc-300">
            <input type="checkbox" checked={filter.trash} onChange={(e) => setFilter({ ...filter, trash: e.target.checked })} />
            {t("trash")}
          </label>
        </div>
        {msg && <p className="text-sm text-rose-300">{msg}</p>}
        {items === null ? <p className="text-sm text-zinc-500">{t("loading")}</p>
          : items.length === 0 ? <p className="text-sm text-zinc-400" data-diagrams-empty>{t(empty)}</p>
          : (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3">
              {items.map((it) => <Tile key={it.id} item={it} onOpen={setOpen} />)}
            </div>
          )}
      </>)}
    </div>
  )
}
