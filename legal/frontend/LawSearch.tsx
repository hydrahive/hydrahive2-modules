import { useEffect, useState } from "react"
import { RefreshCw, Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { legalApi, type NormDetail, type SearchHit, type SyncState } from "./api"
import { citationText, groupLaws, syncSummary, type LawItem } from "./legalFormat"
import { NormView } from "./NormView"

/** Reiter „Gesetze“: Suche (Fachbegriffe oder „§ 536c BGB“), Trefferliste, Wortlaut. Lädt erst auf Eingabe/Klick. */
export function LawSearch() {
  const isAdmin = useAuthStore((s) => s.role === "admin")
  const [q, setQ] = useState("")
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [norm, setNorm] = useState<NormDetail | null>(null)
  const [laws, setLaws] = useState<{ laws: LawItem[]; groups: string[]; core_total: number } | null>(null)
  const [sync, setSync] = useState<SyncState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadMeta = () => {
    legalApi.laws().then(setLaws).catch((e) => setError(String(e.message ?? e)))
    legalApi.syncState().then(setSync).catch(() => {})
  }
  useEffect(loadMeta, [])

  async function run(e?: React.FormEvent) {
    e?.preventDefault()
    if (!q.trim()) return
    setError(null)
    try {
      const res = await legalApi.search(q.trim())
      setHits(res.hits)
      if (res.hits[0]?.match === "exact") await open(res.hits[0])
      else setNorm(null)
    } catch (err) { setError(String((err as Error).message ?? err)) }
  }

  async function open(h: { enbez: string; abbr: string }) {
    try { setNorm(await legalApi.norm(citationText(h.enbez, h.abbr))) } catch (err) { setError(String((err as Error).message ?? err)) }
  }

  async function syncNow() {
    try { await legalApi.syncNow(); setSync((s) => (s ? { ...s, running: true } : s)) } catch (err) { setError(String((err as Error).message ?? err)) }
  }

  const loaded = laws?.laws.length ?? 0
  return (
    <div className="grid min-h-0 gap-[10px] lg:grid-cols-[minmax(320px,420px)_1fr]">
      <section className="min-h-0 space-y-3 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d131d] p-3">
        <form onSubmit={(e) => void run(e)} className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} maxLength={500}
            placeholder="Fachbegriffe oder „§ 536c BGB“"
            className="min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1.5 text-sm text-[#e8eef8]" />
          <button type="submit" className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1.5 text-sm text-white">
            <Search size={14} />Suchen
          </button>
        </form>
        <p className="text-[11px] leading-4 text-[#68758a]">
          Tipp: Wörter aus dem Gesetz treffen besser als Alltagssprache – „Mangel Mietsache Anzeige“ statt „Wohnung zu heiß“.
        </p>
        {error && <p className="text-xs text-rose-300">{error}</p>}
        {hits && hits.length === 0 && <p className="text-sm text-[#8d9ab0]">Keine Treffer. Andere Fachbegriffe versuchen.</p>}
        {hits && hits.length > 0 && (
          <ul className="space-y-1">
            {hits.map((h) => (
              <li key={`${h.abbr}|${h.enbez}`}>
                <button type="button" onClick={() => void open(h)}
                  className="w-full rounded-[4px] border border-transparent p-2 text-left hover:border-[#2a364b] hover:bg-[#111827]">
                  <span className="text-sm font-bold text-[#e8eef8]">{citationText(h.enbez, h.abbr)}</span>
                  <span className="ml-2 text-xs text-[#8d9ab0]">{h.heading}</span>
                  <span className="mt-0.5 block text-xs leading-4 text-[#68758a]">{h.snippet}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {!hits && laws && (
          <div className="space-y-2 text-xs text-[#8d9ab0]">
            <p>{loaded} von {laws.core_total} Gesetzen der Kernliste geladen.</p>
            {groupLaws(laws.laws, laws.groups).map((g) => (
              <p key={g.group}><span className="font-semibold text-[#d7deea]">{g.group}:</span> {g.laws.map((l) => l.abbr).join(", ")}</p>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between gap-2 border-t border-[#2a364b] pt-2 text-[11px] text-[#68758a]">
          <span>{syncSummary(sync?.last ?? null, !!sync?.running)}</span>
          {isAdmin && (
            <button type="button" onClick={() => void syncNow()} disabled={!!sync?.running}
              className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 hover:bg-[#172133] disabled:opacity-50">
              <RefreshCw size={12} />Jetzt abgleichen
            </button>
          )}
        </div>
      </section>
      <section className="min-h-0 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d131d] p-4">
        {norm ? <NormView norm={norm} /> : (
          <p className="text-sm text-[#8d9ab0]">Eine Norm aus der Trefferliste wählen. Der Wortlaut kommt aus dem lokal gespeicherten amtlichen Text.</p>
        )}
      </section>
    </div>
  )
}
