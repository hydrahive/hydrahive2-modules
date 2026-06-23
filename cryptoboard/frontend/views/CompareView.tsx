import { Plus, X } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { CompareChart, type CompareSeries } from "../components/CompareChart"
import { useVs } from "../vsContext"
import type { SearchResult } from "../types"

const C = rgbFor("/cryptoboard")
const PALETTE = ["#34d399", "#60a5fa", "#f472b6", "#fbbf24", "#a78bfa", "#fb923c"]
const TIMEFRAMES = ["7", "30", "90", "365"]
const MAX = 6

interface Pick {
  id: string
  label: string
}

export function CompareView() {
  const { t } = useTranslation("cryptoboard")
  const { vs } = useVs()
  const [picks, setPicks] = useState<Pick[]>([
    { id: "bitcoin", label: "BTC" },
    { id: "ethereum", label: "ETH" },
  ])
  const [days, setDays] = useState("30")
  const [series, setSeries] = useState<CompareSeries[]>([])
  const [loading, setLoading] = useState(false)

  // Coin-Suche
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

  const load = useCallback(async () => {
    if (picks.length === 0) { setSeries([]); return }
    setLoading(true)
    try {
      const charts = await Promise.all(
        picks.map((p) => cryptoApi.chart(p.id, days, vs).then((r) => r.prices).catch(() => [] as [number, number][])),
      )
      setSeries(picks.map((p, i) => ({ id: p.id, label: p.label, color: PALETTE[i % PALETTE.length], prices: charts[i] })))
    } finally {
      setLoading(false)
    }
  }, [picks, days, vs])

  useEffect(() => { void load() }, [load])

  function add(r: SearchResult) {
    if (picks.length >= MAX || picks.some((p) => p.id === r.id)) return
    setPicks((prev) => [...prev, { id: r.id, label: r.symbol || r.name }])
    setQ(""); setResults([]); setOpen(false)
  }

  function remove(id: string) {
    setPicks((prev) => prev.filter((p) => p.id !== id))
  }

  return (
    <div className="p-5 space-y-4 max-w-6xl mx-auto">
      {/* Coin-Chips + Suche */}
      <div className="flex items-center gap-2 flex-wrap">
        {picks.map((p, i) => (
          <span key={p.id} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium"
            style={{ background: `${PALETTE[i % PALETTE.length]}22`, color: PALETTE[i % PALETTE.length] }}>
            {p.label}
            <button onClick={() => remove(p.id)} className="opacity-60 hover:opacity-100"><X size={12} /></button>
          </span>
        ))}
        {picks.length < MAX && (
          <div ref={boxRef} className="relative">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[4%] border border-white/[8%]">
              <Plus size={13} className="text-zinc-500" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("cmp_add_coin")}
                className="w-28 bg-transparent text-xs text-zinc-200 placeholder-zinc-600 outline-none" />
            </div>
            {open && results.length > 0 && (
              <div className="absolute z-30 mt-1 w-56 rounded-lg bg-zinc-900 border border-white/10 shadow-xl overflow-hidden">
                {results.map((r) => (
                  <button key={r.id} onClick={() => add(r)} className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-white/[5%]">
                    {r.thumb && <img src={r.thumb} alt="" className="w-4 h-4 rounded-full" />}
                    <span className="text-sm text-zinc-200">{r.name}</span>
                    <span className="text-xs text-zinc-500 font-mono uppercase">{r.symbol}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Zeitraum */}
      <div className="flex rounded-lg border border-white/10 overflow-hidden text-xs w-fit">
        {TIMEFRAMES.map((d) => (
          <button key={d} onClick={() => setDays(d)}
            className={`px-3 py-1 font-medium transition-colors ${days === d ? "bg-white/10 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>
            {t(`cmp_tf_${d}`)}
          </button>
        ))}
      </div>

      <CollapsibleBox boxId="cryptoboard-compare" color={C} title={t("cmp_title")}>
        <div className="box-b py-3">
          {loading ? (
            <p className="py-12 text-center text-sm text-zinc-500">{t("loading")}</p>
          ) : (
            <CompareChart series={series} />
          )}
        </div>
      </CollapsibleBox>
    </div>
  )
}
