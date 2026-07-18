import { useEffect, useState } from "react"
import { FileClock, FileUp, Inbox } from "lucide-react"
import { errorMessage, haushaltsbuchApi } from "./api"
import { ImportBatchView } from "./ImportBatchView"
import { ImportHistory } from "./ImportHistory"
import { ImportUploadDialog } from "./ImportUploadDialog"
import { formatMinorUnits } from "./money"
import type { Account, Category, ImportBatch, ImportProfile } from "./types"
import { Button, EmptyState, ErrorState, LoadingState, panel } from "./ui"

type Section = "inbox" | "history"

export function ImportsView({ baseCurrency, onChanged }: { baseCurrency: string; onChanged: () => void }) {
  const [accounts, setAccounts] = useState<Account[]>()
  const [categories, setCategories] = useState<Category[]>()
  const [profiles, setProfiles] = useState<ImportProfile[]>()
  const [batches, setBatches] = useState<ImportBatch[]>()
  const [section, setSection] = useState<Section>("inbox")
  const [selected, setSelected] = useState<ImportBatch>()
  const [upload, setUpload] = useState(false)
  const [error, setError] = useState<unknown>()

  async function loadProfiles() { setProfiles(await haushaltsbuchApi.importProfiles()) }
  async function load() {
    setError(undefined)
    try {
      const [nextAccounts, nextCategories, nextProfiles, summaries] = await Promise.all([
        haushaltsbuchApi.accounts(false), haushaltsbuchApi.categories(false),
        haushaltsbuchApi.importProfiles(), haushaltsbuchApi.imports(),
      ])
      const details = await Promise.all(summaries.map((batch) => haushaltsbuchApi.importBatch(batch.id)))
      setAccounts(nextAccounts); setCategories(nextCategories); setProfiles(nextProfiles); setBatches(details)
    } catch (cause) { setError(cause) }
  }
  useEffect(() => { void load() }, [])

  async function openBatch(batch: ImportBatch) {
    setError(undefined)
    try { setSelected(batch.rows ? batch : await haushaltsbuchApi.importBatch(batch.id)) }
    catch (cause) { setError(cause) }
  }
  function batchChanged(next: ImportBatch) {
    setBatches((current) => current?.map((batch) => batch.id === next.id ? next : batch) ?? [next])
    setSelected((current) => current?.id === next.id ? next : current)
    onChanged()
  }
  function created(batch: ImportBatch) {
    setBatches((current) => [batch, ...(current ?? [])]); setUpload(false); setSelected(batch); onChanged()
  }
  function deleted(batchId: number) {
    setBatches((current) => current?.filter((batch) => batch.id !== batchId) ?? [])
    setSelected(undefined)
    onChanged()
  }

  if (error && (!accounts || !categories || !profiles || !batches)) return <ErrorState error={errorMessage(error)} onRetry={load} />
  if (!accounts || !categories || !profiles || !batches) return <LoadingState label="Import-Inbox wird geladen …" />
  const hasImportableAccount = accounts.some((account) => !account.archived && account.currency === baseCurrency)
  if (selected) return <><ImportBatchView initialBatch={selected} accounts={accounts} categories={categories} onBack={() => setSelected(undefined)} onChanged={batchChanged} onDeleted={deleted} />{upload && <ImportUploadDialog accounts={accounts} baseCurrency={baseCurrency} profiles={profiles} onProfilesChanged={loadProfiles} onClose={() => setUpload(false)} onCreated={created} />}</>

  const drafts = batches.filter((batch) => batch.status === "draft")
  const historical = batches.filter((batch) => batch.status !== "draft")
  return <div className="space-y-4">
    {error !== undefined && <ErrorState error={errorMessage(error)} onRetry={load} />}
    <div className="flex flex-wrap items-center gap-2"><div className="mr-auto"><h2 className="flex items-center gap-2 font-bold text-[#e8eef8]"><Inbox size={17} className="text-cyan-300" />Bankimport-Inbox</h2><p className="mt-1 text-xs text-[#8d9ab0]">Bankexporte werden zuerst als persistente Entwürfe geprüft und erst nach Bestätigung gebucht.</p></div><Button tone="primary" onClick={() => setUpload(true)} disabled={!hasImportableAccount}><FileUp size={13} className="mr-1 inline" />Neuer Import</Button></div>
    {!hasImportableAccount && <ErrorState error={`Lege zuerst ein aktives Konto in der Haushaltsbasiswährung ${baseCurrency} an.`} />}
    <div className="flex gap-1 border-b border-[#263247]"><button type="button" onClick={() => setSection("inbox")} className={`flex items-center gap-2 border-b-2 px-3 py-2 text-xs font-bold ${section === "inbox" ? "border-cyan-300 text-cyan-200" : "border-transparent text-[#8d9ab0]"}`}><Inbox size={14} />Inbox ({drafts.length})</button><button type="button" onClick={() => setSection("history")} className={`flex items-center gap-2 border-b-2 px-3 py-2 text-xs font-bold ${section === "history" ? "border-cyan-300 text-cyan-200" : "border-transparent text-[#8d9ab0]"}`}><FileClock size={14} />Historie ({historical.length})</button></div>
    {section === "inbox" && (drafts.length ? <div className="grid gap-3 lg:grid-cols-2">{drafts.map((batch) => {
      const rows = batch.rows ?? []; const account = accounts.find((item) => item.id === batch.account_id); const dates = rows.flatMap((row) => row.booking_date ? [row.booking_date] : []).sort(); const errors = rows.filter((row) => row.status === "error").length; const duplicates = rows.filter((row) => row.status === "duplicate").length
      return <button key={batch.id} type="button" onClick={() => openBatch(batch)} className={`${panel} p-4 text-left transition hover:border-cyan-400/40`}><div className="flex items-start gap-3"><div className="min-w-0 flex-1"><h3 className="truncate font-bold text-[#e8eef8]">{batch.display_filename}</h3><p className="mt-1 text-xs text-[#8d9ab0]">{batch.source_format.toUpperCase()} · {account?.name ?? `Konto #${batch.account_id}`}</p></div><span className="rounded border border-cyan-400/30 bg-cyan-400/10 px-2 py-1 text-[11px] font-bold text-cyan-200">Entwurf</span></div><div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4"><div><span className="text-[#718097]">Zeilen</span><strong className="block text-[#d4deeb]">{rows.length}</strong></div><div><span className="text-[#718097]">Summe</span><strong className="block text-[#d4deeb]">{formatMinorUnits(rows.reduce((sum, row) => sum + (row.amount_minor ?? 0), 0), account?.currency ?? rows.find((row) => row.currency)?.currency ?? "EUR")}</strong></div><div><span className="text-[#718097]">Zeitraum</span><strong className="block text-[#d4deeb]">{dates.length ? `${dates[0]} – ${dates[dates.length - 1]}` : "—"}</strong></div><div><span className="text-[#718097]">Prüfung</span><strong className={errors ? "block text-rose-200" : duplicates ? "block text-amber-200" : "block text-emerald-200"}>{errors} Fehler · {duplicates} Duplikate</strong></div></div></button>
    })}</div> : <EmptyState title="Inbox ist leer" text="Lade einen CAMT-, MT940- oder CSV-Bankexport hoch. Der Upload erzeugt noch keine Buchungen." action={<Button tone="primary" onClick={() => setUpload(true)} disabled={!hasImportableAccount}>Bankexport auswählen</Button>} />)}
    {section === "history" && <ImportHistory batches={batches} accounts={accounts} onOpen={openBatch} onChanged={batchChanged} />}
    {upload && <ImportUploadDialog accounts={accounts} baseCurrency={baseCurrency} profiles={profiles} onProfilesChanged={loadProfiles} onClose={() => setUpload(false)} onCreated={created} />}
  </div>
}
