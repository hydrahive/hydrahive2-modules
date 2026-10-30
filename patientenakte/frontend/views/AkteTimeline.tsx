import { useTranslation } from "react-i18next"
import { useEffect, useState, type CSSProperties } from "react"
import { akteApi, type AkteEntityKey, type AkteTimelineEntry } from "../api"
import { useAkteSchema } from "../useAkteSchema"
import { VerifyBadge } from "../components/VerifyBadge"

const ENTITY_ICONS: Record<string, string> = {
  conditions:    "🔴",
  medications:   "💊",
  observations:  "🧪",
  events:        "📋",
  imaging:       "🩻",
  allergies:     "⚠️",
  practitioners: "👨‍⚕️",
  documents:     "📄",
  notes:         "📝",
}

type FilterEntity = AkteEntityKey | "all"

export function AkteTimeline() {
  const { t } = useTranslation("akte")
  const schema = useAkteSchema()
  const [entries, setEntries] = useState<AkteTimelineEntry[] | null>(null)
  const [filter, setFilter] = useState<FilterEntity>("all")
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    akteApi.getTimeline()
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleVerify = async (entity: AkteEntityKey, eid: string) => {
    await akteApi.verifyEntity(entity, eid)
    setEntries((prev) =>
      prev?.map((e) => eid === e.record?.id || e.record?.id === eid
        ? { ...e, verifiziert: 1 }
        : e
      ) ?? null
    )
  }

  if (loading) {
    return <div className="h-48 rounded-xl bg-[rgb(var(--hh-s-box,21_28_43)/0.5)] animate-pulse" />
  }

  const filtered = filter === "all"
    ? entries
    : entries?.filter((e) => e.entity === filter)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter("all")}
          className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
            filter === "all"
              ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
              : "text-[#9aa7bc] border-[rgb(var(--hh-s-rand,42_54_75))] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
          }`}
        >
          Alle
        </button>
        {(Object.keys(ENTITY_ICONS) as AkteEntityKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors border flex items-center gap-1.5 ${
              filter === key
                ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                : "text-[#9aa7bc] border-[rgb(var(--hh-s-rand,42_54_75))] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
            }`}
          >
            <span>{ENTITY_ICONS[key]}</span>
            <span>{schema?.entities[key]?.label ?? key}</span>
          </button>
        ))}
      </div>

      {(!filtered || filtered.length === 0) && (
        <p className="text-sm text-[#9aa7bc] py-8 text-center">
          {entries === null ? t("loading") : t("akte.empty_entries")}
        </p>
      )}

      {filtered && filtered.length > 0 && (
        <div className="relative pl-6">
          <div className="absolute left-2 top-0 bottom-0 w-px bg-[rgb(var(--hh-s-innen,17_24_39))]" />
          {filtered.map((entry) => (
            <div key={entry.record?.id as string ?? entry.sort_date + entry.entity} className="relative mb-4">
              <div
                className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${
                  entry.verifiziert ? "bg-emerald-400" : "bg-orange-400"
                }`}
              />
              <div className="box overflow-hidden px-3 py-2" style={{ "--c": "105 215 255" } as CSSProperties}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <VerifyBadge verifiziert={entry.verifiziert} onVerify={() => {
                      if (!entry.verifiziert) {
                        handleVerify(entry.entity, entry.record?.id as string)
                      }
                    }} />
                    <span className="text-sm text-[#e8eef8] truncate">{entry.label}</span>
                  </div>
                  <span className="text-xs text-[#9aa7bc] shrink-0">
                    {entry.sort_date ? new Date(entry.sort_date).toLocaleDateString("de-DE") : ""}
                  </span>
                </div>
                <span className="text-xs text-[#9aa7bc]">{ENTITY_ICONS[entry.entity]} {schema?.entities[entry.entity]?.label ?? entry.entity}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}