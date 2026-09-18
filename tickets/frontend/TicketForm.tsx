import { useState } from "react"
import type { FormEvent } from "react"
import { ArrowLeft, FilePlus2, Info } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Input, Select, Textarea } from "@/shared/ui"
import { ticketsApi } from "./api"
import type { Ticket, TicketPriority } from "./types"

interface Props {
  onCreated: (ticket: Ticket) => void
  onCancel: () => void
}

export function TicketForm({ onCreated, onCancel }: Props) {
  const { t } = useTranslation("tickets")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState<TicketPriority>("normal")
  const [category, setCategory] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    setError(false)
    try {
      onCreated(await ticketsApi.create({ title: title.trim(), description: description.trim(), priority, category: category.trim() }))
    } catch {
      setError(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[780px]">
      <button type="button" onClick={onCancel} className="mb-5 inline-flex items-center gap-2 text-xs font-medium text-[#8191a6] transition-colors hover:text-[#c8f2ff]"><ArrowLeft size={14} />{t("backToInbox")}</button>
      <form onSubmit={(event) => void submit(event)} className="overflow-hidden rounded-[8px] border border-[#1f2a3b] bg-[#0d1420]">
        <header className="border-b border-[#1f2a3b] px-5 py-5 lg:px-7">
          <div className="flex items-start gap-3"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-[7px] border border-[#2b4058] bg-[#132235] text-[#69d7ff]"><FilePlus2 size={17} /></div><div><h2 className="text-lg font-semibold text-[#f1f5fb]">{t("newTicket")}</h2><p className="mt-1 text-xs leading-relaxed text-[#718096]">{t("internalOnly")}</p></div></div>
        </header>
        <div className="space-y-5 px-5 py-6 lg:px-7">
          {error && <div className="flex items-start gap-2 rounded-[6px] border border-orange-500/25 bg-orange-500/[7%] px-3 py-2.5 text-xs text-orange-200"><Info size={14} className="mt-0.5 shrink-0" />{t("saveError")}</div>}
          <label className="block"><span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.1em] text-[#8d9ab0]">{t("titleField")}</span><Input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required placeholder={t("titlePlaceholder")} className="border-[#253247] bg-[#111b29]" /></label>
          <label className="block"><span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.1em] text-[#8d9ab0]">{t("descriptionField")}</span><Textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={20000} rows={8} placeholder={t("descriptionPlaceholder")} className="border-[#253247] bg-[#111b29] leading-6" /></label>
          <div className="grid gap-4 sm:grid-cols-2"><label className="block"><span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.1em] text-[#8d9ab0]">{t("priorityLabel")}</span><Select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="border-[#253247] bg-[#111b29]"><option value="low">{t("priority.low")}</option><option value="normal">{t("priority.normal")}</option><option value="high">{t("priority.high")}</option><option value="urgent">{t("priority.urgent")}</option></Select></label><label className="block"><span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.1em] text-[#8d9ab0]">{t("categoryField")}</span><Input value={category} onChange={(event) => setCategory(event.target.value)} maxLength={80} placeholder={t("categoryPlaceholder")} className="border-[#253247] bg-[#111b29]" /></label></div>
        </div>
        <footer className="flex items-center justify-end gap-2 border-t border-[#1f2a3b] bg-[#0b131f] px-5 py-4 lg:px-7"><button type="button" onClick={onCancel} className="rounded-[6px] px-3 py-2 text-xs font-medium text-[#8191a6] transition-colors hover:bg-[#172133] hover:text-[#d1dae6]">{t("cancel")}</button><button disabled={busy || !title.trim()} className="rounded-[6px] border border-[#3b83a8] bg-[#163248] px-4 py-2 text-xs font-semibold text-[#c8f2ff] transition-colors hover:border-[#69d7ff] hover:bg-[#1b3d56] disabled:cursor-not-allowed disabled:opacity-40">{busy ? t("saving") : t("create")}</button></footer>
      </form>
    </div>
  )
}
