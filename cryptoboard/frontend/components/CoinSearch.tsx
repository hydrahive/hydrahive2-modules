import { Search, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { SearchResult } from "../types"

export function CoinSearch() {
  const { t } = useTranslation("cryptoboard")
  const nav = useNavigate()
  const [q, setQ] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const term = q.trim()
    if (term.length < 2) {
      setResults([])
      return
    }
    const h = setTimeout(() => {
      cryptoApi.search(term)
        .then((r) => { setResults(r.slice(0, 8)); setOpen(true) })
        .catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(h)
  }, [q])

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [])

  function pick(id: string) {
    setQ("")
    setResults([])
    setOpen(false)
    nav(`/cryptoboard/coin/${id}`)
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-900/70 border border-white/[8%] focus-within:border-white/20 transition-colors">
        <Search size={15} className="text-zinc-500 shrink-0" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={t("search_placeholder")}
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 outline-none"
        />
        {q && (
          <button onClick={() => { setQ(""); setResults([]) }} className="text-zinc-600 hover:text-zinc-300 shrink-0">
            <X size={14} />
          </button>
        )}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg bg-zinc-900 border border-white/10 shadow-xl shadow-black/40 overflow-hidden">
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => pick(r.id)}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-left hover:bg-white/[5%] transition-colors"
            >
              {r.thumb && <img src={r.thumb} alt="" className="w-5 h-5 rounded-full" />}
              <span className="text-sm text-zinc-200">{r.name}</span>
              <span className="text-xs text-zinc-500 font-mono uppercase">{r.symbol}</span>
              {r.market_cap_rank && <span className="ml-auto text-[10px] text-zinc-600">#{r.market_cap_rank}</span>}
            </button>
          ))}
        </div>
      )}
      {open && q.trim().length >= 2 && results.length === 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg bg-zinc-900 border border-white/10 px-3 py-2 text-sm text-zinc-500">
          {t("search_empty")}
        </div>
      )}
    </div>
  )
}
