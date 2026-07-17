import { useEffect, useState } from "react"
import { Eye, RotateCcw } from "lucide-react"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import type { Account, ImportBatch } from "./types"
import { Button, EmptyState, ErrorState, LoadingState, panel } from "./ui"

const BATCH_STATUS = { imported: "Importiert", reversed: "Storniert", draft: "Entwurf" } as const

export function ImportHistory({ batches, accounts, onOpen, onChanged }: {
  batches: ImportBatch[]
  accounts: Account[]
  onOpen: (batch: ImportBatch) => void
  onChanged: (batch: ImportBatch) => void
}) {
  const history = batches.filter((batch) => batch.status !== "draft")
  const [details, setDetails] = useState<Record<number, ImportBatch>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>()
  const [reverse, setReverse] = useState<ImportBatch>()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!history.length) { setDetails({}); return }
    let cancelled = false; setLoading(true); setError(undefined)
    Promise.all(history.map((batch) => haushaltsbuchApi.importBatch(batch.id))).then((items) => {
      if (!cancelled) setDetails(Object.fromEntries(items.map((item) => [item.id, item])))
    }).catch((cause) => { if (!cancelled) setError(cause) }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [batches])

  async function confirmReverse() {
    if (!reverse) return
    setBusy(true); setError(undefined)
    try {
      const next = await haushaltsbuchApi.reverseImport(reverse.id, reverse.revision)
      setDetails((current) => ({ ...current, [next.id]: next })); setReverse(undefined); onChanged(next)
    } catch (cause) { setError(cause); setReverse(undefined) } finally { setBusy(false) }
  }

  if (!history.length) return <EmptyState title="Noch keine Importhistorie" text="Abgeschlossene und stornierte Importpakete erscheinen dauerhaft hier." />
  if (loading && !Object.keys(details).length) return <LoadingState label="Importhistorie wird geladen …" />
  return <div className="space-y-3">
    {error !== undefined && <ErrorState error={errorMessage(error)} conflict={isConflict(error)} />}
    {history.map((summary) => {
      const batch = details[summary.id] ?? summary
      const rows = batch.rows ?? []
      const account = accounts.find((item) => item.id === batch.account_id)
      const dates = rows.flatMap((row) => row.booking_date ? [row.booking_date] : []).sort()
      const imported = rows.filter((row) => row.status === "imported" || row.status === "reversed").length
      const rejected = rows.filter((row) => row.status === "rejected" || row.status === "duplicate").length
      const failed = rows.filter((row) => row.status === "error").length
      return <article key={batch.id} className={`${panel} p-4`}>
        <div className="flex flex-wrap items-start gap-3"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="truncate font-bold text-[#e8eef8]">{batch.display_filename}</h3><span className="rounded border border-[#40506a] px-2 py-0.5 text-[11px] font-bold text-[#c4cfdd]">{BATCH_STATUS[batch.status]}</span></div><p className="mt-1 text-xs text-[#8d9ab0]">{batch.source_format.toUpperCase()} · {account?.name ?? `Konto #${batch.account_id}`} · {dates.length ? `${dates[0]} – ${dates[dates.length - 1]}` : "Zeitraum wird geladen"}</p><p className="mt-2 text-xs text-[#718097]">Gebucht: {imported} · Verworfen/Duplikat: {rejected} · Fehlerhaft: {failed}</p></div><Button onClick={() => onOpen(batch)}><Eye size={13} className="mr-1 inline" />Details</Button>{batch.status === "imported" && <Button tone="danger" onClick={() => setReverse(batch)}><RotateCcw size={13} className="mr-1 inline" />Paket stornieren</Button>}</div>
      </article>
    })}
    {reverse && <AdminConfirmDialog title="Gesamten Import stornieren?" confirmLabel={busy ? "Wird storniert …" : "Import vollständig stornieren"} cancelLabel="Abbrechen" busy={busy} onClose={() => setReverse(undefined)} onConfirm={confirmReverse}>Für „{reverse.display_filename}“ werden Gegenbuchungen zu allen noch aktiven importierten Vorgängen erzeugt. Das Importpaket kann nicht ein zweites Mal storniert werden.</AdminConfirmDialog>}
  </div>
}
