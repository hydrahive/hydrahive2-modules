import { useState, type ReactNode } from "react"
import { Download } from "lucide-react"
import { errorMessage } from "./api"
import type { ReportResult } from "./useReport"
import { Button, EmptyState, ErrorState, LoadingState, panel } from "./ui"

interface Props<T> {
  title: string
  hint: string
  state: ReportResult<T> | undefined
  retry: () => void
  isEmpty: (data: T) => boolean
  emptyText?: string
  csv: () => Promise<void>
  extra?: ReactNode
  chart: (data: T) => ReactNode
  table: (data: T) => ReactNode
}

/** Rahmen je Diagramm: Titel, CSV-Knopf, Lade-/Fehler-/Leerzustand und die Tabellenalternative. */
export function ReportCard<T>({ title, hint, state, retry, isEmpty, emptyText, csv, extra, chart, table }: Props<T>) {
  const [busy, setBusy] = useState(false)
  const [csvError, setCsvError] = useState<string>()
  const download = () => { setBusy(true); setCsvError(undefined); csv().catch((e) => setCsvError(errorMessage(e))).finally(() => setBusy(false)) }
  let body: ReactNode
  if (!state) body = <LoadingState label="Auswertung wird berechnet …" />
  else if (!state.ok) body = <ErrorState error={errorMessage(state.error)} onRetry={retry} />
  else if (isEmpty(state.data)) body = <EmptyState title="Noch nichts auszuwerten" text={emptyText ?? "In diesem Zeitraum gibt es noch keine passenden Buchungen."} />
  else body = <>
    {chart(state.data)}
    <details className="mt-3 text-sm"><summary className="cursor-pointer text-xs font-bold text-cyan-200">Als Tabelle anzeigen</summary><div className="mt-2">{table(state.data)}</div></details>
  </>
  return <section className={`${panel} p-4`} aria-label={title}>
    <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
      <div><h2 className="font-bold text-[#e8eef8]">{title}</h2><p className="mt-0.5 text-xs text-[#9aa7bc]">{hint}</p></div>
      <div className="flex flex-wrap items-end gap-2">{extra}<Button onClick={download} disabled={busy || !state?.ok} aria-label={`${title} als CSV-Datei herunterladen`}><Download size={13} className="mr-1 inline" />{busy ? "Lädt …" : "CSV"}</Button></div>
    </div>
    {csvError && <p className="mb-2 text-xs text-rose-200" role="alert">Der Export hat nicht geklappt: {csvError}</p>}
    {body}
  </section>
}
