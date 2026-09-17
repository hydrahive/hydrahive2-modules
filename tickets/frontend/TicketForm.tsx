import { useState } from "react"
import type { FormEvent } from "react"
import { useTranslation } from "react-i18next"
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
    setBusy(true); setError(false)
    try { onCreated(await ticketsApi.create({ title: title.trim(), description, priority, category })) } catch { setError(true) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto w-full max-w-2xl space-y-4 rounded-2xl border border-white/10 bg-zinc-950/40 p-6">
      <div><h1 className="text-xl font-semibold text-zinc-100">{t("newTicket")}</h1><p className="mt-1 text-sm text-zinc-500">{t("internalOnly")}</p></div>
      {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{t("saveError")}</div>}
      <label className="block text-sm text-zinc-400">{t("titleField")}<input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-zinc-100 outline-none focus:border-sky-400/50" /></label>
      <label className="block text-sm text-zinc-400">{t("descriptionField")}<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={20000} rows={7} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-sky-400/50" /></label>
      <div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm text-zinc-400">{t("priorityLabel")}<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"><option value="low">{t("priority.low")}</option><option value="normal">{t("priority.normal")}</option><option value="high">{t("priority.high")}</option><option value="urgent">{t("priority.urgent")}</option></select></label><label className="block text-sm text-zinc-400">{t("categoryField")}<input value={category} onChange={(event) => setCategory(event.target.value)} maxLength={80} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100" /></label></div>
      <div className="flex justify-end gap-2"><button type="button" onClick={onCancel} className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:bg-white/5">{t("cancel")}</button><button disabled={busy || !title.trim()} className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-40">{busy ? t("saving") : t("create")}</button></div>
    </form>
  )
}
