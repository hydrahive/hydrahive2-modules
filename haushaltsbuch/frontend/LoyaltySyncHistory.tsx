import type { LoyaltySyncRun } from "./loyaltyTypes"
import { Button, EmptyState, panel } from "./ui"

const STATUS = {
  running: "Läuft", succeeded: "Erfolgreich", partial: "Teilweise",
  failed: "Fehlgeschlagen", cancelled: "Abgebrochen",
}

export function LoyaltySyncHistory({ runs, onClose }: {
  runs: LoyaltySyncRun[]
  onClose: () => void
}) {
  return <section className={`${panel} p-4`} aria-label="Synchronisationsverlauf">
    <div className="mb-3 flex items-center justify-between gap-3">
      <div><h3 className="font-bold text-[#e8eef8]">Sync-Verlauf</h3><p className="text-xs text-[#8d9ab0]">Technische Details ohne Zugangsdaten oder Einkaufsinhalte.</p></div>
      <Button onClick={onClose}>Schließen</Button>
    </div>
    {!runs.length ? <EmptyState title="Noch keine Synchronisierung" text="Nach dem ersten manuellen Sync erscheint der Lauf hier." /> : <div className="space-y-2">{runs.map((run) => <div key={run.id} className="rounded border border-[#2b374b] bg-[#0b111c] p-3 text-xs">
      <div className="flex flex-wrap justify-between gap-2"><strong className={run.status === "failed" ? "text-rose-200" : "text-[#e8eef8]"}>{STATUS[run.status]}</strong><span className="text-[#718097]">{new Date(run.started_at).toLocaleString("de-DE")}</span></div>
      <p className="mt-1 text-[#8d9ab0]">Gelesen {run.fetched_count} · Neu {run.created_count} · Aktualisiert {run.updated_count} · Übersprungen {run.skipped_count}</p>
      {run.error_code && <p className="mt-1 text-rose-200">{run.error_code.replaceAll("_", " ")}</p>}
    </div>)}</div>}
  </section>
}
