import { useCallback, useEffect, useState } from "react"
import { RefreshCw, X } from "lucide-react"
import { errorMessage } from "./api"
import { loyaltyApi } from "./loyaltyApi"
import type { PaybackDataResult } from "./loyaltyTypes"
import { Button, EmptyState, ErrorState, LoadingState, panel } from "./ui"

const integer = new Intl.NumberFormat("de-DE")
const ACTIVITY = { earn: "Gesammelt", redeem: "Eingelöst", expire: "Verfallen", reversal: "Storno", adjustment: "Korrektur" }
const COUPON = { available: "Verfügbar", activated: "Aktiviert", redeemed: "Eingelöst", expired: "Abgelaufen", unavailable: "Nicht verfügbar" }
const EXPIRATION = { scheduled: "Angekündigt", expired: "Verfallen", cancelled: "Entfallen" }

function date(value: string | null): string {
  if (!value) return "–"
  const [year, month, day] = value.slice(0, 10).split("-").map(Number)
  return Number.isFinite(year + month + day) ? new Date(year, month - 1, day).toLocaleDateString("de-DE") : value
}

function dateTime(value: string): string {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("de-DE")
}

function money(amountMinor: number, currency: string): string {
  try {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency }).format(amountMinor / 100)
  } catch {
    return `${(amountMinor / 100).toFixed(2)} ${currency}`
  }
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className={`${panel} p-3`}><p className="text-[10px] font-bold uppercase tracking-wider text-[#718097]">{label}</p><p className="mt-1 text-xl font-black text-[#e8eef8]">{value}</p>{hint && <p className="mt-1 text-[11px] text-[#8d9ab0]">{hint}</p>}</div>
}

export function PaybackData({ connectionId, refreshKey, onClose }: {
  connectionId: number
  refreshKey: number
  onClose: () => void
}) {
  const [data, setData] = useState<PaybackDataResult>()
  const [error, setError] = useState<unknown>()
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true); setError(undefined)
    loyaltyApi.paybackData(connectionId)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [connectionId])
  useEffect(load, [load, refreshKey])

  return <section className="space-y-4 border-t border-[#2a364b] pt-5">
    <div className="flex flex-wrap items-start gap-3">
      <div className="min-w-0 flex-1"><h3 className="text-base font-bold text-[#e8eef8]">PAYBACK-Daten</h3><p className="mt-1 text-xs text-[#8d9ab0]">Read-only Ansicht des zuletzt bestätigten Browser-Imports.</p></div>
      <Button disabled={loading} onClick={load}><RefreshCw size={13} className="mr-1 inline" />Neu laden</Button>
      <Button aria-label="Datenansicht schließen" onClick={onClose}><X size={13} /></Button>
    </div>
    {loading && !data ? <LoadingState label="PAYBACK-Daten werden geladen …" /> : error !== undefined ? <ErrorState error={errorMessage(error)} onRetry={load} /> : data ? <PaybackContent data={data} /> : null}
  </section>
}

function PaybackContent({ data }: { data: PaybackDataResult }) {
  const purchaseTotal = data.metrics.purchase_totals.length
    ? data.metrics.purchase_totals.map((item) => money(item.amount_minor, item.currency)).join(" · ")
    : "Keine Beträge"
  const couponCount = Object.values(data.metrics.coupon_status).reduce((sum, count) => sum + count, 0)

  return <div className="space-y-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Metric label="Punktestand" value={data.latest_balance ? integer.format(data.latest_balance.available_points) : "–"} hint={data.latest_balance ? `Stand ${dateTime(data.latest_balance.observed_at)}` : "Noch nicht erfasst"} />
      <Metric label="Aktivitäten" value={integer.format(data.metrics.activity_count)} />
      <Metric label="Gesammelt" value={`${integer.format(data.metrics.points_collected)} P`} />
      <Metric label="Eingelöst" value={`${integer.format(data.metrics.points_redeemed)} P`} />
      <Metric label="Sichtbare Einkäufe" value={purchaseTotal} hint="Nur eindeutig erkennbare Beträge" />
    </div>

    <section className={`${panel} overflow-hidden`}>
      <div className="border-b border-[#263247] px-4 py-3"><h4 className="font-bold text-[#e8eef8]">Angekündigter Punkteverfall</h4></div>
      {data.expirations.length === 0 ? <p className="p-4 text-sm text-[#8d9ab0]">Kein Punkteverfall erfasst.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="bg-[#131b2a] text-[#8d9ab0]"><tr><th className="px-4 py-2">Datum</th><th className="px-4 py-2">Punkte</th><th className="px-4 py-2">Status</th></tr></thead><tbody>{data.expirations.map((item) => <tr key={item.id} className="border-t border-[#202b3d] text-[#d4deeb]"><td className="px-4 py-2">{date(item.expiration_date)}</td><td className="px-4 py-2 font-bold">{integer.format(item.points)}</td><td className="px-4 py-2">{EXPIRATION[item.status]}</td></tr>)}</tbody></table></div>}
    </section>

    <div className="grid gap-4 lg:grid-cols-2">
      <section className={`${panel} p-4`}><h4 className="font-bold text-[#e8eef8]">Partnerhäufigkeit</h4>{data.metrics.partner_frequency.length === 0 ? <p className="mt-3 text-sm text-[#8d9ab0]">Noch keine Partneraktivitäten erfasst.</p> : <ol className="mt-3 grid gap-2">{data.metrics.partner_frequency.map((partner, index) => <li key={partner.partner_id} className="flex items-center gap-3 text-sm"><span className="w-5 text-right text-xs text-[#718097]">{index + 1}.</span><span className="min-w-0 flex-1 truncate text-[#d4deeb]">{partner.name}</span><strong className="text-cyan-200">{integer.format(partner.activity_count)}×</strong></li>)}</ol>}</section>
      <section className={`${panel} p-4`}><h4 className="font-bold text-[#e8eef8]">Coupon-Kennzahlen</h4><p className="mt-1 text-xs text-[#8d9ab0]">{integer.format(couponCount)} erfasste Coupons nach sichtbarem Status</p>{couponCount === 0 ? <p className="mt-3 text-sm text-[#8d9ab0]">Noch keine Coupons erfasst.</p> : <div className="mt-3 flex flex-wrap gap-2">{Object.entries(data.metrics.coupon_status).map(([status, count]) => <span key={status} className="rounded border border-[#33425a] bg-[#172133] px-2 py-1 text-xs text-[#d4deeb]">{COUPON[status as keyof typeof COUPON] ?? status}: <strong>{integer.format(count)}</strong></span>)}</div>}</section>
    </div>

    <section className={`${panel} overflow-hidden`}>
      <div className="border-b border-[#263247] px-4 py-3"><h4 className="font-bold text-[#e8eef8]">Punkteaktivitäten</h4><p className="mt-1 text-[11px] text-[#718097]">Maximal die neuesten {integer.format(data.limits.activities)} Einträge</p></div>
      {data.activities.length === 0 ? <EmptyState title="Keine Aktivitäten" text="Beim letzten Browser-Import wurden keine Punkteaktivitäten erfasst." /> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-[#131b2a] text-[#8d9ab0]"><tr><th className="px-4 py-2">Datum</th><th className="px-4 py-2">Partner / Beschreibung</th><th className="px-4 py-2">Art</th><th className="px-4 py-2 text-right">Einkauf</th><th className="px-4 py-2 text-right">Punkte</th></tr></thead><tbody>{data.activities.map((item) => <tr key={item.id} className="border-t border-[#202b3d] text-[#d4deeb]"><td className="whitespace-nowrap px-4 py-3">{date(item.activity_date)}</td><td className="max-w-md px-4 py-3"><strong>{item.partner_name || "Unbekannter Partner"}</strong>{item.original_description && <p className="mt-0.5 text-[#8d9ab0]">{item.original_description}</p>}</td><td className="px-4 py-3">{ACTIVITY[item.activity_type]}</td><td className="whitespace-nowrap px-4 py-3 text-right">{item.purchase_amount_minor !== null && item.purchase_currency ? money(item.purchase_amount_minor, item.purchase_currency) : "–"}</td><td className={`whitespace-nowrap px-4 py-3 text-right font-bold ${item.points_delta > 0 ? "text-emerald-200" : item.points_delta < 0 ? "text-amber-200" : ""}`}>{item.points_delta > 0 ? "+" : ""}{integer.format(item.points_delta)}</td></tr>)}</tbody></table></div>}
    </section>

    <section className={`${panel} overflow-hidden`}>
      <div className="border-b border-[#263247] px-4 py-3"><h4 className="font-bold text-[#e8eef8]">Coupons</h4><p className="mt-1 text-[11px] text-[#718097]">Nur Anzeige – keine Aktivierung oder Einlösung</p></div>
      {data.coupons.length === 0 ? <EmptyState title="Keine Coupons" text="Beim letzten Browser-Import wurden keine Coupons erfasst." /> : <div className="grid gap-3 p-4 md:grid-cols-2">{data.coupons.map((coupon) => <article key={coupon.id} className="rounded border border-[#2a364b] bg-[#0b111c] p-3"><div className="flex items-start gap-2"><div className="min-w-0 flex-1"><p className="text-[11px] font-bold uppercase tracking-wide text-cyan-200">{coupon.partner_name || "PAYBACK"}</p><h5 className="mt-1 font-bold text-[#e8eef8]">{coupon.title}</h5></div><span className="shrink-0 rounded border border-[#33425a] px-2 py-1 text-[10px] text-[#b5c1d2]">{COUPON[coupon.activation_status]}</span></div>{coupon.description && <p className="mt-2 text-xs text-[#9eacc0]">{coupon.description}</p>}<div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#8d9ab0]"><span>Gültig: {date(coupon.valid_from)} – {date(coupon.valid_until)}</span>{coupon.multiplier && <strong className="text-emerald-200">{coupon.multiplier}×</strong>}{coupon.bonus_points !== null && <strong className="text-emerald-200">+{integer.format(coupon.bonus_points)} Punkte</strong>}</div>{coupon.condition_text && <p className="mt-2 border-t border-[#202b3d] pt-2 text-[11px] text-[#718097]">{coupon.condition_text}</p>}</article>)}</div>}
    </section>
  </div>
}
