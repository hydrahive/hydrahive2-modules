import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, Eye, ReceiptText, RefreshCw, Tag } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage } from "./api"
import { loyaltyApi } from "./loyaltyApi"
import type { LoyaltyReceipt, LoyaltyReceiptAdjustment, LoyaltyReceiptDetail } from "./loyaltyTypes"
import { formatMinorUnits } from "./money"
import { Button, EmptyState, ErrorState, LoadingState, panel } from "./ui"

const kindLabel = { discount: "Rabatt", coupon: "Coupon", deposit: "Pfand", rounding: "Rundung" }
const unitLabel = { piece: "Stk.", kg: "kg" }

function amount(value: number | null, currency: string | null) {
  return value === null || !currency ? "—" : formatMinorUnits(value, currency, "de-DE")
}

function purchased(value: string | null) {
  return value ? new Date(value).toLocaleString("de-DE") : "Zeitpunkt unbekannt"
}

function ReceiptDetailDialog({ receipt, onClose }: { receipt: LoyaltyReceiptDetail; onClose: () => void }) {
  const adjustmentItem = (entry: LoyaltyReceiptAdjustment) =>
    entry.item_id === null ? undefined : receipt.items.find((item) => item.id === entry.item_id)?.original_name
  return <AdminDialog title={`${receipt.merchant_name} · ${amount(receipt.total_minor, receipt.currency)}`} eyebrow="Kundenkarten · Read-only-Beleg" icon={<ReceiptText size={16} />} maxWidthClass="max-w-4xl" onClose={onClose} footer={<Button onClick={onClose}>Schließen</Button>}>
    <div className="grid gap-4 text-sm text-[#d4deeb]">
      <section className="grid gap-2 rounded border border-[#2a364b] bg-[#0b111c] p-3 sm:grid-cols-2">
        <div><span className="text-xs text-[#718097]">Einkauf</span><p>{purchased(receipt.purchased_at)}</p></div>
        <div><span className="text-xs text-[#718097]">Filiale</span><p>{receipt.store_name || "Unbekannte Filiale"}</p>{receipt.store_address && <p className="text-xs text-[#8d9ab0]">{receipt.store_address}</p>}</div>
        <div><span className="text-xs text-[#718097]">Gesamt</span><p className="font-bold text-[#e8eef8]">{amount(receipt.total_minor, receipt.currency)}</p></div>
        <div><span className="text-xs text-[#718097]">Rabatte gesamt</span><p>{amount(receipt.total_discount_minor, receipt.currency)}</p></div>
      </section>
      {receipt.validation_status === "needs_review" && <div className="rounded border border-amber-400/35 bg-amber-400/10 p-3 text-xs text-amber-100"><strong>Bitte prüfen:</strong> Der Provider-Beleg enthält unvollständige oder widersprüchliche Daten.{receipt.warnings.length > 0 && <ul className="mt-1 list-disc pl-5">{receipt.warnings.map((warning) => <li key={warning}>{warning.replaceAll("_", " ")}</li>)}</ul>}</div>}
      <section><h3 className="mb-2 font-bold text-[#e8eef8]">Artikel ({receipt.items.length})</h3>{receipt.items.length === 0 ? <p className="text-xs text-[#8d9ab0]">Keine Artikel übermittelt.</p> : <div className="overflow-x-auto rounded border border-[#2a364b]"><table className="w-full min-w-[640px] text-left text-xs"><thead className="bg-[#172133] text-[#9eacc0]"><tr><th className="p-2">Artikel</th><th className="p-2">Menge</th><th className="p-2 text-right">Einzelpreis</th><th className="p-2 text-right">Summe</th></tr></thead><tbody>{receipt.items.map((item) => <tr key={item.id} className="border-t border-[#263247]"><td className="p-2"><strong className="text-[#dce5f2]">{item.original_name}</strong>{item.gtin && <span className="mt-0.5 block text-[11px] text-[#718097]">GTIN {item.gtin}</span>}{item.is_return && <span className="text-amber-200">Retoure</span>}</td><td className="p-2">{item.quantity ?? "—"} {item.unit ? unitLabel[item.unit] : ""}</td><td className="p-2 text-right">{amount(item.unit_price_minor, receipt.currency)}</td><td className="p-2 text-right font-bold">{amount(item.total_minor, receipt.currency)}</td></tr>)}</tbody></table></div>}</section>
      <section><h3 className="mb-2 flex items-center gap-2 font-bold text-[#e8eef8]"><Tag size={15} />Rabatte, Coupons, Pfand & Rundung</h3>{receipt.adjustments.length === 0 ? <p className="text-xs text-[#8d9ab0]">Keine Anpassungen übermittelt.</p> : <div className="grid gap-2">{receipt.adjustments.map((entry) => <div key={entry.id} className="flex items-start justify-between gap-3 rounded border border-[#2a364b] p-2 text-xs"><div><strong>{kindLabel[entry.kind]}</strong>{entry.description && <span className="ml-2 text-[#9eacc0]">{entry.description}</span>}{adjustmentItem(entry) && <p className="text-[11px] text-[#718097]">Artikel: {adjustmentItem(entry)}</p>}</div><strong>{amount(entry.amount_minor, receipt.currency)}</strong></div>)}</div>}</section>
      <p className="text-xs text-[#718097]">Inoffizielle, experimentelle Lidl-Daten. Diese Ansicht ist ausschließlich read-only und verändert keine Buchungen.</p>
    </div>
  </AdminDialog>
}

export function LoyaltyReceipts({ refreshKey = 0 }: { refreshKey?: number }) {
  const [receipts, setReceipts] = useState<LoyaltyReceipt[]>()
  const [detail, setDetail] = useState<LoyaltyReceiptDetail>()
  const [busyId, setBusyId] = useState<number>()
  const [error, setError] = useState<unknown>()
  const load = useCallback(() => {
    setError(undefined)
    loyaltyApi.receipts().then(setReceipts).catch(setError)
  }, [])
  useEffect(load, [load, refreshKey])

  async function open(receipt: LoyaltyReceipt) {
    setBusyId(receipt.id); setError(undefined)
    try { setDetail(await loyaltyApi.receipt(receipt.id)) }
    catch (cause) { setError(cause) } finally { setBusyId(undefined) }
  }

  return <section className="space-y-3">
    <header className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-bold text-[#e8eef8]">Synchronisierte Lidl-Belege</h3><p className="mt-1 text-xs text-[#8d9ab0]">Experimentell, inoffiziell und read-only: Artikel, Rabatte und Pfand aus der letzten manuellen Synchronisierung.</p></div><Button onClick={load}><RefreshCw size={13} className="mr-1 inline" />Neu laden</Button></header>
    {error !== undefined && <ErrorState error={errorMessage(error)} onRetry={load} />}
    {receipts === undefined ? <LoadingState label="Belege werden geladen …" /> : receipts.length === 0 ? <EmptyState title="Noch keine Lidl-Belege" text="Starte bei der aktiven Lidl-Verbindung eine manuelle Synchronisierung." /> : <div className="grid gap-2">{receipts.map((receipt) => <article key={receipt.id} className={`${panel} flex flex-wrap items-center gap-3 p-3`}><ReceiptText size={18} className="text-cyan-200" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><strong className="text-sm text-[#e8eef8]">{receipt.store_name || receipt.merchant_name}</strong>{receipt.validation_status === "needs_review" && <span className="flex items-center gap-1 text-[11px] text-amber-200"><AlertTriangle size={11} />Prüfen</span>}</div><p className="mt-1 text-xs text-[#8d9ab0]">{purchased(receipt.purchased_at)} · {amount(receipt.total_minor, receipt.currency)}{receipt.total_discount_minor ? ` · Rabatt ${amount(receipt.total_discount_minor, receipt.currency)}` : ""}</p></div><Button disabled={busyId !== undefined} onClick={() => open(receipt)}><Eye size={13} className="mr-1 inline" />{busyId === receipt.id ? "Lädt …" : "Details"}</Button></article>)}</div>}
    {detail && <ReceiptDetailDialog receipt={detail} onClose={() => setDetail(undefined)} />}
  </section>
}
