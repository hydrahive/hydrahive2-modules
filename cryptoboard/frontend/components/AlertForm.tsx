import { Search } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { AlertInput, AlertKind, SearchResult } from "../types"

interface Props {
  onSaved: () => void
  onCancel: () => void
}

const COIN_KINDS: AlertKind[] = ["price_above", "price_below", "pct_change_24h_above", "pct_change_24h_below"]
const PF_KINDS: AlertKind[] = ["portfolio_above", "portfolio_below"]

function isPortfolio(kind: AlertKind): boolean {
  return kind === "portfolio_above" || kind === "portfolio_below"
}

export function AlertForm({ onSaved, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [kind, setKind] = useState<AlertKind>("price_above")
  const [coin, setCoin] = useState<{ id: string; symbol: string } | null>(null)
  const [threshold, setThreshold] = useState("")
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")

  const [q, setQ] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const term = q.trim()
    if (term.length < 2) { setResults([]); return }
    const h = setTimeout(() => {
      cryptoApi.search(term).then((r) => { setResults(r.slice(0, 6)); setOpen(true) }).catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(h)
  }, [q])

  const portfolio = isPortfolio(kind)

  async function submit() {
    setErr("")
    if (!portfolio && !coin) { setErr(t("al_err_coin")); return }
    const th = parseFloat(threshold)
    if (Number.isNaN(th)) { setErr(t("al_err_threshold")); return }
    const body: AlertInput = {
      kind,
      coin_id: portfolio ? "" : (coin?.id ?? ""),
      symbol: portfolio ? "" : (coin?.symbol ?? ""),
      threshold: th,
      note: "",
    }
    setBusy(true)
    try {
      await cryptoApi.addAlert(body)
      onSaved()
    } catch {
      setErr(t("al_err_save"))
    } finally {
      setBusy(false)
    }
  }

  const fieldCls = "w-full px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%] text-sm text-zinc-200 outline-none focus:border-white/20"
  const allKinds = [...COIN_KINDS, ...PF_KINDS]

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {allKinds.map((k) => (
          <button key={k} onClick={() => setKind(k)}
            className={`px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${kind === k ? "bg-white/10 text-white" : "bg-white/[3%] text-zinc-400 hover:text-zinc-200"}`}>
            {t(`al_kind_${k}`)}
          </button>
        ))}
      </div>

      {!portfolio && (
        coin ? (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[4%] border border-white/[8%]">
            <span className="text-sm text-zinc-200 font-mono uppercase">{coin.symbol}</span>
            <button onClick={() => setCoin(null)} className="ml-auto text-xs text-zinc-500 hover:text-zinc-300">{t("tx_cancel")}</button>
          </div>
        ) : (
          <div ref={boxRef} className="relative">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%]">
              <Search size={15} className="text-zinc-500" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search_placeholder")}
                className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 outline-none" />
            </div>
            {open && results.length > 0 && (
              <div className="absolute z-30 mt-1 w-full rounded-lg bg-zinc-900 border border-white/10 shadow-xl overflow-hidden">
                {results.map((r) => (
                  <button key={r.id} onClick={() => { setCoin({ id: r.id, symbol: r.symbol }); setOpen(false); setQ("") }}
                    className="flex items-center gap-2.5 w-full px-3 py-2 text-left hover:bg-white/[5%]">
                    {r.thumb && <img src={r.thumb} alt="" className="w-5 h-5 rounded-full" />}
                    <span className="text-sm text-zinc-200">{r.name}</span>
                    <span className="text-xs text-zinc-500 font-mono uppercase">{r.symbol}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )
      )}

      <label className="space-y-1 block">
        <span className="text-xs text-zinc-500">{portfolio || kind.startsWith("portfolio") ? t("al_threshold_eur") : kind.startsWith("pct") ? t("al_threshold_pct") : t("al_threshold_eur")}</span>
        <input type="number" step="any" value={threshold} onChange={(e) => setThreshold(e.target.value)} className={fieldCls} placeholder="0.00" />
      </label>

      {err && <p className="text-xs text-rose-400">{err}</p>}

      <div className="flex items-center gap-2 pt-1">
        <button disabled={busy} onClick={submit}
          className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-sm font-medium hover:bg-emerald-500/30 disabled:opacity-50">
          {t("al_create")}
        </button>
        <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-white/[4%] text-zinc-400 text-sm hover:text-zinc-200">
          {t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
