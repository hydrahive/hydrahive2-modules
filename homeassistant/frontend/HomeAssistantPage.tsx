import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw, Search } from "lucide-react"
import { useHomeAssistant } from "./useHomeAssistant"
import { groupByDomain } from "./entityControl"
import { ConnectionBanner } from "./components/ConnectionBanner"
import { EntityRow } from "./components/EntityRow"
import type { HAState } from "./api"

export function HomeAssistantPage() {
  const { t } = useTranslation("homeassistant")
  const { test, states, favorites, loading, error, busy, load, toggle, toggleFavorite } =
    useHomeAssistant()
  const [query, setQuery] = useState("")
  const [favOnly, setFavOnly] = useState(false)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return states.filter((s) => {
      if (favOnly && !favorites.has(s.entity_id)) return false
      if (!q) return true
      return `${s.entity_id} ${s.name}`.toLowerCase().includes(q)
    })
  }, [states, query, favOnly, favorites])

  const groups = useMemo(() => groupByDomain(filtered), [filtered])

  const renderRow = (e: HAState) => (
    <EntityRow
      key={e.entity_id}
      entity={e}
      isFavorite={favorites.has(e.entity_id)}
      busy={busy.has(e.entity_id)}
      onToggle={toggle}
      onToggleFavorite={toggleFavorite}
    />
  )

  return (
    <div className="p-6 space-y-5 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-sm text-zinc-500">{t("subtitle")}</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-40"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          {t("refresh")}
        </button>
      </div>

      <ConnectionBanner test={test} error={error} />

      {test?.ok && (
        <>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("search_placeholder")}
                className="w-full rounded-lg border border-white/10 bg-zinc-900 pl-9 pr-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-white/20"
              />
            </div>
            <button
              onClick={() => setFavOnly((v) => !v)}
              className={`rounded-lg px-3 py-2 text-sm transition-colors ${
                favOnly ? "bg-amber-500/20 text-amber-300" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
            >
              {t("favorites_only")}
            </button>
          </div>

          {loading ? (
            <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
          ) : filtered.length === 0 ? (
            <p className="text-sm text-zinc-500">{t("empty")}</p>
          ) : (
            <div className="space-y-5">
              {groups.map(([domain, entities]) => (
                <section key={domain} className="space-y-2">
                  <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                    {domain} <span className="text-zinc-600">({entities.length})</span>
                  </h2>
                  <div className="space-y-1.5">{entities.map(renderRow)}</div>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
