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
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[rgb(var(--hh-s-box,21_28_43)/0.7)] border border-[rgb(var(--hh-s-rand,42_54_75))] focus-within:border-[rgb(var(--hh-s-rand-hover,70_97_127))] transition-colors">
        <Search size={15} className="text-[#9aa7bc] shrink-0" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={t("search_placeholder")}
          className="flex-1 bg-transparent text-sm text-[#e8eef8] placeholder-[#9aa7bc] outline-none"
        />
        {q && (
          <button onClick={() => { setQ(""); setResults([]) }} className="text-[#9aa7bc] hover:text-[#c8d2df] shrink-0">
            <X size={14} />
          </button>
        )}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] shadow-xl shadow-black/40 overflow-hidden">
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => pick(r.id)}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-left hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] transition-colors"
            >
              {r.thumb && <img src={r.thumb} alt="" className="w-5 h-5 rounded-full" />}
              <span className="text-sm text-[#e8eef8]">{r.name}</span>
              <span className="text-xs text-[#9aa7bc] font-mono uppercase">{r.symbol}</span>
              {r.market_cap_rank && <span className="ml-auto text-[10px] text-[#9aa7bc]">#{r.market_cap_rank}</span>}
            </button>
          ))}
        </div>
      )}
      {open && q.trim().length >= 2 && results.length === 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2 text-sm text-[#9aa7bc]">
          {t("search_empty")}
        </div>
      )}
    </div>
  )
}
