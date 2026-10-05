import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { miningApi } from "../api"
import { bestRoi, cloreLine, gpuLabel, toEur, type CloreSummary } from "../clore"
import { formatPercent } from "../format"

const POLL_MS = 5 * 60_000
const eur = (v: number | null) => (v === null ? "—" : `${v.toFixed(2)} €`)
const pct = (v: number | null) => (v === null ? "—" : formatPercent(v))

/** Clore-Probelauf: Würde sich Mieten lohnen? Nur gerechnet, nichts gemietet. */
export function ClorePanel({ usdPerEur }: { usdPerEur: number | null }) {
  const { t } = useTranslation("mining")
  const [data, setData] = useState<CloreSummary | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => miningApi.clore().then((d) => { if (alive) setData(d) }).catch(() => undefined)
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  if (!data) return null
  const line = cloreLine(data.last_run)
  const hits = data.hits_24h.slice(0, 8)
  return (
    <section className="space-y-2 rounded-xl border border-white/10 p-4">
      <h2 className="text-sm font-semibold text-zinc-200">{t("clore_title")}</h2>
      <p className="text-xs text-zinc-500">{t("clore_note")}</p>
      <p className="text-sm text-zinc-300">
        {line.kind === "never" && t("clore_never")}
        {line.kind === "error" && <span className="text-amber-300">{t("clore_error", { error: line.error })}</span>}
        {line.kind === "none" && t("clore_none", { n: line.rated, best: pct(line.best) })}
        {line.kind === "hits" && <span className="text-emerald-300">{t("clore_hits", { n: line.rated, hits: line.hits, best: pct(line.best) })}</span>}
      </p>
      {hits.length > 0 && (
        <table className="w-full text-xs">
          <thead className="text-zinc-500"><tr>
            <th className="py-1 text-left">{t("clore_col_gpu")}</th><th className="text-left">Coin</th>
            <th className="text-right">{t("clore_col_revenue")}</th><th className="text-right">{t("clore_col_cost")}</th>
            <th className="text-right">ROI</th><th className="text-right">Server</th>
          </tr></thead>
          <tbody className="text-zinc-300">
            {hits.map((h) => {
              const b = bestRoi(h)
              const cost = b.kind === "spot" ? h.cost_spot : h.cost_od
              return (
                <tr key={`${h.server_id}-${h.ts}`} className="border-t border-white/5">
                  <td className="py-1">{gpuLabel(h.gpu, h.count)}{h.source === "measured" ? " ✓" : ""}</td>
                  <td>{h.coin.toUpperCase()}</td>
                  <td className="text-right">{eur(toEur(h.revenue, usdPerEur))}</td>
                  <td className="text-right">{eur(toEur(cost, usdPerEur))}{b.kind === "spot" ? " (Spot)" : ""}</td>
                  <td className="text-right text-emerald-300">{pct(b.roi)}</td>
                  <td className="text-right text-zinc-500">{h.server_id}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      {data.days.length > 0 && (
        <p className="text-xs text-zinc-500">
          {data.days.slice(-7).map((d) => t("clore_day", { day: d.day.slice(5), hit: d.runs_with_hits, runs: d.runs })).join(" · ")}
        </p>
      )}
    </section>
  )
}
