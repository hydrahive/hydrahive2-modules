import { useMemo, useState } from "react"
import { ArrowLeft, Check, CheckCheck, Pencil, Save, X } from "lucide-react"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { formatMinorUnits, minorToInput, parseMinorUnits } from "./money"
import type { Account, Category, ImportBatch, ImportRow, ImportRowStatus, ImportRowUpdate } from "./types"
import { Button, EmptyState, ErrorState, Input, Select, Textarea, panel } from "./ui"

const STATUS_LABEL: Record<ImportRowStatus, string> = {
  pending: "Offen", accepted: "Angenommen", rejected: "Verworfen", duplicate: "Duplikat",
  error: "Fehler", imported: "Gebucht", reversed: "Storniert",
}
const FILTERS: { value: "all" | ImportRowStatus; label: string }[] = [
  { value: "all", label: "Alle" }, { value: "pending", label: "Offen" },
  { value: "accepted", label: "Angenommen" }, { value: "rejected", label: "Verworfen" },
  { value: "duplicate", label: "Duplikate" }, { value: "error", label: "Fehler" },
]
const messageLabel = (value: string) => ({
  possible_duplicate: "Mögliches Duplikat (schwacher Treffer)",
  account_currency_mismatch: "Währung passt nicht zum Zielkonto",
}[value] ?? value.replaceAll("_", " "))

function RowEditor({ batchId, row, accountCurrency, categories, readOnly, onUpdated }: {
  batchId: number
  row: ImportRow
  accountCurrency: string
  categories: Category[]
  readOnly: boolean
  onUpdated: (row: ImportRow) => void
}) {
  const [editing, setEditing] = useState(false)
  const [date, setDate] = useState(row.booking_date ?? "")
  const currency = accountCurrency
  const [amount, setAmount] = useState(minorToInput(row.amount_minor ?? 0, accountCurrency))
  const [counterparty, setCounterparty] = useState(row.counterparty ?? "")
  const [purpose, setPurpose] = useState(row.purpose ?? "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const matchingCategories = categories.filter((category) => !category.archived && category.kind === ((row.amount_minor ?? 0) > 0 ? "income" : "expense"))

  async function patch(update: Omit<ImportRowUpdate, "revision">): Promise<boolean> {
    setBusy(true); setError(undefined)
    try { onUpdated(await haushaltsbuchApi.updateImportRow(batchId, row.id, { revision: row.revision, ...update })); return true }
    catch (cause) { setError(cause); return false } finally { setBusy(false) }
  }
  async function save() {
    try {
      if (!date) throw new Error("Gib ein gültiges Buchungsdatum ein.")
      const saved = await patch({
        booking_date: date,
        amount_minor: parseMinorUnits(amount, currency),
        currency,
        counterparty: counterparty.trim() || null,
        purpose: purpose.trim() || null,
      })
      if (saved) setEditing(false)
    } catch (cause) { setError(cause) }
  }

  return <article className={`${panel} p-4`}>
    <div className="flex flex-wrap items-start gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2"><strong className="text-sm text-[#e8eef8]">{row.counterparty || "Ohne Gegenpartei"}</strong><span className="rounded border border-[#40506a] px-2 py-0.5 text-[11px] font-bold text-[#c4cfdd]">{STATUS_LABEL[row.status]}</span>{row.fingerprint_strength === "weak" && row.warnings.includes("possible_duplicate") && <span className="text-[11px] font-bold text-amber-200">Schwaches Duplikat</span>}</div>
        <p className="mt-1 break-words text-xs text-[#8d9ab0]">{row.purpose || "Kein Verwendungszweck"}</p>
        <p className="mt-2 text-[11px] text-[#718097]">{row.booking_date ?? "Ungültiges Datum"}{row.value_date ? ` · Valuta ${row.value_date}` : ""} · Quellzeile {row.source_line}{row.category_hint ? ` · Hinweis: ${row.category_hint}` : ""}</p>
      </div>
      <strong className={`tabular-nums ${(row.amount_minor ?? -1) >= 0 ? "text-emerald-200" : "text-[#e8eef8]"}`}>{row.amount_minor === null || row.currency === null ? "—" : formatMinorUnits(row.amount_minor, row.currency)}</strong>
    </div>
    {(row.warnings.length > 0 || row.errors.length > 0) && <ul className="mt-3 space-y-1 text-xs">{row.warnings.map((warning) => <li key={`w-${warning}`} className="text-amber-200">Warnung: {messageLabel(warning)}</li>)}{row.errors.map((item) => <li key={`e-${item}`} className="text-rose-200">Fehler: {messageLabel(item)}</li>)}</ul>}
    {error !== undefined && <div className="mt-3"><ErrorState error={errorMessage(error)} conflict={isConflict(error)} /></div>}
    {!readOnly && <div className="mt-4 grid gap-3 border-t border-[#263247] pt-3 lg:grid-cols-[minmax(12rem,1fr)_auto_auto]">
      <Select aria-label="Kategorie" value={row.category_id ?? ""} disabled={busy} onChange={(event) => patch({ category_id: event.target.value ? Number(event.target.value) : null })}><option value="">Kategorie wählen …</option>{matchingCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select>
      <div className="flex gap-2"><Button disabled={busy || row.errors.length > 0} tone={row.status === "accepted" ? "primary" : "default"} onClick={() => patch({ status: "accepted" })}><Check size={13} className="mr-1 inline" />Annehmen</Button><Button disabled={busy} tone={row.status === "rejected" ? "danger" : "default"} onClick={() => patch({ status: "rejected" })}><X size={13} className="mr-1 inline" />Verwerfen</Button></div>
      <Button disabled={busy} onClick={() => setEditing(!editing)}><Pencil size={13} className="mr-1 inline" />Korrigieren</Button>
    </div>}
    {editing && !readOnly && <div className="mt-3 grid gap-3 rounded border border-[#33425a] bg-[#0b111c] p-3 sm:grid-cols-2"><Input aria-label="Buchungsdatum" type="date" value={date} onChange={(event) => setDate(event.target.value)} /><Input aria-label={`Betrag in ${currency}`} value={amount} onChange={(event) => setAmount(event.target.value)} /><Input aria-label="Währung" value={currency} readOnly /><Input aria-label="Gegenpartei" maxLength={240} value={counterparty} onChange={(event) => setCounterparty(event.target.value)} /><div className="sm:col-span-2"><Textarea aria-label="Verwendungszweck" rows={2} maxLength={500} value={purpose} onChange={(event) => setPurpose(event.target.value)} /></div><div className="flex gap-2 sm:col-span-2"><Button tone="primary" disabled={busy} onClick={save}><Save size={13} className="mr-1 inline" />Speichern</Button><Button disabled={busy} onClick={() => setEditing(false)}>Abbrechen</Button></div></div>}
  </article>
}

export function ImportBatchView({ initialBatch, accounts, categories, onBack, onChanged }: {
  initialBatch: ImportBatch
  accounts: Account[]
  categories: Category[]
  onBack: () => void
  onChanged: (batch: ImportBatch) => void
}) {
  const [batch, setBatch] = useState(initialBatch)
  const [filter, setFilter] = useState<"all" | ImportRowStatus>("all")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const [confirmComplete, setConfirmComplete] = useState(false)
  const rows = batch.rows ?? []
  const account = accounts.find((item) => item.id === batch.account_id)
  const accepted = rows.filter((row) => row.status === "accepted")
  const acceptedSum = accepted.reduce((sum, row) => sum + (row.amount_minor ?? 0), 0)
  const missingCategory = accepted.filter((row) => row.category_id === null).length
  const visibleRows = filter === "all" ? rows : rows.filter((row) => row.status === filter)
  const dates = rows.flatMap((row) => row.booking_date ? [row.booking_date] : []).sort()
  const counts = useMemo(() => rows.reduce<Partial<Record<ImportRowStatus, number>>>((result, row) => ({ ...result, [row.status]: (result[row.status] ?? 0) + 1 }), {}), [rows])

  function updateRow(next: ImportRow) {
    const nextBatch = { ...batch, rows: rows.map((row) => row.id === next.id ? next : row) }
    setBatch(nextBatch); onChanged(nextBatch)
  }
  async function bulk(status: "accepted" | "rejected") {
    const candidates = rows.filter((row) => row.errors.length === 0 && row.status !== "duplicate" && row.status !== "imported" && row.status !== "reversed" && row.status !== status)
    if (!candidates.length) return
    setBusy(true); setError(undefined)
    try {
      const changed = new Map<number, ImportRow>()
      for (const row of candidates) changed.set(row.id, await haushaltsbuchApi.updateImportRow(batch.id, row.id, { revision: row.revision, status }))
      const next = { ...batch, rows: rows.map((row) => changed.get(row.id) ?? row) }
      setBatch(next); onChanged(next)
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function complete() {
    setBusy(true); setError(undefined)
    try { const next = await haushaltsbuchApi.completeImport(batch.id, batch.revision); setBatch(next); setConfirmComplete(false); onChanged(next) }
    catch (cause) { setError(cause); setConfirmComplete(false) } finally { setBusy(false) }
  }

  return <div className="space-y-4">
    <div className="flex flex-wrap items-center gap-3"><Button onClick={onBack}><ArrowLeft size={13} className="mr-1 inline" />Zur Übersicht</Button><div className="min-w-0 flex-1"><h2 className="truncate font-bold text-[#e8eef8]">{batch.display_filename}</h2><p className="text-xs text-[#8d9ab0]">{batch.source_format.toUpperCase()} · {account?.name ?? `Konto #${batch.account_id}`} · Paket #{batch.id}</p></div>{batch.status === "draft" && <Button tone="primary" disabled={!accepted.length || missingCategory > 0 || busy} onClick={() => setConfirmComplete(true)}><CheckCheck size={13} className="mr-1 inline" />Import abschließen</Button>}</div>
    {batch.status === "imported" && <div className="rounded border border-emerald-500/35 bg-emerald-500/10 p-4 text-sm text-emerald-100" role="status"><strong>Import abgeschlossen.</strong> {rows.filter((row) => row.status === "imported").length} Zeilen wurden verbindlich gebucht.</div>}
    {batch.status === "reversed" && <div className="rounded border border-amber-500/35 bg-amber-500/10 p-4 text-sm text-amber-100" role="status"><strong>Import storniert.</strong> Die zugehörigen Buchungen wurden durch Gegenbuchungen aufgehoben.</div>}
    {error !== undefined && <ErrorState error={errorMessage(error)} conflict={isConflict(error)} />}
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <div className={`${panel} p-3`}><span className="text-xs text-[#718097]">Zeilen</span><strong className="mt-1 block text-lg text-[#e8eef8]">{rows.length}</strong></div>
      <div className={`${panel} p-3`}><span className="text-xs text-[#718097]">Zeitraum</span><strong className="mt-1 block text-sm text-[#e8eef8]">{dates.length ? `${dates[0]} – ${dates[dates.length - 1]}` : "—"}</strong></div>
      <div className={`${panel} p-3`}><span className="text-xs text-[#718097]">Gesamtsumme</span><strong className="mt-1 block text-sm text-[#e8eef8]">{formatMinorUnits(rows.reduce((sum, row) => sum + (row.amount_minor ?? 0), 0), account?.currency ?? rows.find((row) => row.currency)?.currency ?? "EUR")}</strong></div>
      <div className={`${panel} p-3`}><span className="text-xs text-[#718097]">Duplikate</span><strong className="mt-1 block text-lg text-amber-200">{counts.duplicate ?? 0}</strong></div>
      <div className={`${panel} p-3`}><span className="text-xs text-[#718097]">Fehler</span><strong className="mt-1 block text-lg text-rose-200">{counts.error ?? 0}</strong></div>
    </section>
    {batch.status === "draft" && <div className="flex flex-wrap items-center gap-2"><div className="mr-auto flex flex-wrap gap-1">{FILTERS.map((item) => <button key={item.value} type="button" onClick={() => setFilter(item.value)} className={`rounded border px-2 py-1 text-xs font-bold ${filter === item.value ? "border-cyan-400/40 bg-cyan-400/15 text-cyan-200" : "border-[#33425a] text-[#8d9ab0]"}`}>{item.label}{item.value !== "all" ? ` (${counts[item.value] ?? 0})` : ` (${rows.length})`}</button>)}</div><Button disabled={busy} onClick={() => bulk("accepted")}>Alle gültigen annehmen</Button><Button disabled={busy} onClick={() => bulk("rejected")}>Alle gültigen verwerfen</Button></div>}
    {batch.status === "draft" && missingCategory > 0 && <p className="text-xs font-semibold text-amber-200">{missingCategory} angenommene Zeile(n) benötigen vor dem Abschluss eine passende Kategorie.</p>}
    <div className="space-y-3">{visibleRows.map((row) => <RowEditor key={row.id} batchId={batch.id} row={row} accountCurrency={account?.currency ?? "EUR"} categories={categories} readOnly={batch.status !== "draft"} onUpdated={updateRow} />)}{!visibleRows.length && <EmptyState title="Keine Zeilen" text="Für diesen Filter sind keine Importzeilen vorhanden." />}</div>
    {confirmComplete && <AdminConfirmDialog title="Import verbindlich abschließen?" confirmLabel={busy ? "Wird gebucht …" : "Verbindlich buchen"} cancelLabel="Weiter prüfen" confirmTone="primary" busy={busy} onClose={() => setConfirmComplete(false)} onConfirm={complete}>{accepted.length} Zeile(n) mit einer Summe von {formatMinorUnits(acceptedSum, account?.currency ?? accepted[0]?.currency ?? "EUR")} werden atomar gebucht. Dieser Schritt verändert das Ledger.</AdminConfirmDialog>}
  </div>
}
