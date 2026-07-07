import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw, Search, Star, X } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { useHomeAssistant } from "./useHomeAssistant"
import { groupByDomain } from "./entityControl"
import { ConnectionBanner } from "./components/ConnectionBanner"
import { DomainChips } from "./components/DomainChips"
import { DomainSection } from "./components/DomainSection"
import { EntityRow } from "./components/EntityRow"
import type { HAState } from "./api"

export function HomeAssistantPage() {
  const { t } = useTranslation("homeassistant")
  const { test, states, favorites, loading, error, busy, load, toggle, toggleFavorite } =
    useHomeAssistant()
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState<string | null>(null) // null=alle | "__fav__" | domain

  // Suchfilter zuerst
  const searched = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return states
    return states.filter((s) => `${s.entity_id} ${s.name}`.toLowerCase().includes(q))
  }, [states, query])

  // Favoriten-Liste (immer aus den gesuchten States)
  const favList = useMemo(
    () => searched.filter((s) => favorites.has(s.entity_id))
      .sort((a, b) => a.name.localeCompare(b.name)),
    [searched, favorites],
  )

  // Domain-gefilterte Hauptliste
  const visible = useMemo(() => {
    if (filter === "__fav__") return favList
    if (filter) return searched.filter((s) => s.domain === filter)
    return searched
  }, [searched, filter, favList])

  const groups = useMemo(() => groupByDomain(visible), [visible])
  // Beim Suchen oder aktivem Filter: Gruppen offen. Sonst eingeklappt.
  const sectionsOpen = Boolean(query.trim()) || filter !== null
  const searching = Boolean(query.trim())

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
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      {/* Sticky-Header: Titel, Refresh, Suche, Chips */}
      <div className="sticky top-0 z-10 -mx-4 sm:-mx-6 px-4 sm:px-6 pb-3 pt-1 bg-zinc-950/80 backdrop-blur space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1">
            <div>
              <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
              {test?.ok && test.config?.location_name && (
                <p className="text-xs text-zinc-500">{test.config.location_name}</p>
              )}
            </div>
            <HelpButton topic="homeassistant" />
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-40"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span className="hidden sm:inline">{t("refresh")}</span>
          </button>
        </div>

        {test?.ok && (
          <>
            <div className="relative">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("search_placeholder")}
                className="w-full rounded-lg border border-white/10 bg-zinc-900 pl-9 pr-9 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-white/20"
              />
              {query && (
                <button
                  onClick={() => setQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                >
                  <X size={15} />
                </button>
              )}
            </div>
            <DomainChips states={searched} favCount={favList.length} active={filter} onSelect={setFilter} />
          </>
        )}
      </div>

      <div className="mt-4 space-y-4">
        <ConnectionBanner test={test} error={error} />

        {test?.ok && (
          loading ? (
            <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
          ) : visible.length === 0 ? (
            <p className="py-8 text-center text-sm text-zinc-500">{t("empty")}</p>
          ) : (
            <>
              {/* Favoriten-Schnellzugriff oben — nur ohne aktiven Filter/Suche */}
              {filter === null && !searching && favList.length > 0 && (
                <section className="space-y-2">
                  <h2 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-amber-400/80">
                    <Star size={13} fill="currentColor" /> {t("favorites")}
                  </h2>
                  <div className="space-y-1.5">{favList.map(renderRow)}</div>
                </section>
              )}

              {/* Favoriten-Filter aktiv: flache Liste */}
              {filter === "__fav__" ? (
                <div className="space-y-1.5">{favList.map(renderRow)}</div>
              ) : (
                <div className="space-y-2.5">
                  {groups.map(([domain, entities]) => (
                    <DomainSection
                      key={domain}
                      domain={domain}
                      entities={entities}
                      favorites={favorites}
                      busy={busy}
                      defaultOpen={sectionsOpen}
                      onToggle={toggle}
                      onToggleFavorite={toggleFavorite}
                    />
                  ))}
                </div>
              )}
            </>
          )
        )}
      </div>
    </div>
  )
}
