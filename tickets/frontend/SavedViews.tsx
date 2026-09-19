import { Bookmark, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { ticketsApi, type SavedView, type TicketFilters } from "./api"

interface Props {
  views: SavedView[]
  filters: TicketFilters
  onApply: (filters: TicketFilters) => void
  onChanged: () => void
}

export function SavedViews({ views, filters, onApply, onChanged }: Props) {
  const { t } = useTranslation("tickets")
  const [selected, setSelected] = useState("")
  const [name, setName] = useState("")
  async function save() {
    if (!name.trim()) return
    await ticketsApi.createView({ name: name.trim(), filters, sort: filters.sort ?? "updated_at", direction: filters.direction ?? "desc" })
    setName("")
    onChanged()
  }
  async function remove() {
    if (!selected) return
    await ticketsApi.deleteView(selected)
    setSelected("")
    onChanged()
  }
  return <div className="border-b border-[#1f2a3b] bg-[#0b131f] px-3 py-2">
    <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#718096]"><Bookmark size={11} className="text-[#69d7ff]" />{t("savedViews")}</div>
    <div className="flex gap-1.5"><select value={selected} onChange={(event) => { setSelected(event.target.value); const view = views.find((item) => item.id === event.target.value); if (view) onApply(view.filters) }} className="min-w-0 flex-1 rounded-[5px] border border-[#253247] bg-[#111b29] px-2 py-1.5 text-[11px] text-[#b7c4d3]"><option value="">{t("chooseView")}</option>{views.map((view) => <option key={view.id} value={view.id}>{view.name}</option>)}</select><button disabled={!selected} onClick={() => void remove()} className="grid h-7 w-7 place-items-center rounded-[5px] border border-[#253247] text-[#718096] hover:border-orange-400/50 hover:text-orange-300 disabled:opacity-40" title={t("deleteView")}><Trash2 size={12} /></button></div>
    <div className="mt-1.5 flex gap-1.5"><input value={name} onChange={(event) => setName(event.target.value)} placeholder={t("viewName")} className="min-w-0 flex-1 rounded-[5px] border border-[#253247] bg-[#111b29] px-2 py-1.5 text-[11px] text-[#b7c4d3]" /><button disabled={!name.trim()} onClick={() => void save()} className="grid h-7 w-7 place-items-center rounded-[5px] border border-[#253247] text-[#718096] hover:border-[#69d7ff]/60 hover:text-[#c8f2ff] disabled:opacity-40" title={t("saveView")}><Plus size={12} /></button></div>
  </div>
}
