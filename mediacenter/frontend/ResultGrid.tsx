import { LayoutGrid, List } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { GroupDetail } from "./GroupDetail"
import { PosterCard } from "./PosterCard"
import { ResultList } from "./ResultList"
import type { ResultGroup, SearchResponse } from "./types"

interface Props {
  response: SearchResponse | null
  searched: boolean
  error: string | null
  onQueued: () => void
}

/**
 * Ergebnisdarstellung mit zwei Ansichten:
 * - Raster (Standard): Poster-Kacheln, ein Titel = eine Kachel
 * - Liste: die flache V1-Darstellung — schneller zu scannen und die einzige
 *   sinnvolle Ansicht für Bücher, die der Indexer ohne Cover liefert.
 */
export function ResultGrid({ response, searched, error, onQueued }: Props) {
  const { t } = useTranslation("mediacenter")
  const [mode, setMode] = useState<"grid" | "list">("grid")
  const [openGroup, setOpenGroup] = useState<ResultGroup | null>(null)

  if (error) return <div className="rounded-[6px] border border-rose-500/25 bg-rose-500/[8%] p-4 text-sm text-rose-200" role="alert">{error}</div>
  if (!searched) return <Empty text={t("results.initial")} />
  if (!response?.results.length) return <Empty text={t("results.empty")} />

  // Die geöffnete Gruppe aus der aktuellen Antwort neu auflösen, damit eine
  // frische Suche keine veraltete Detailansicht stehen lässt.
  const active = openGroup ? response.groups.find((group) => group.key === openGroup.key) ?? null : null
  if (active) return <GroupDetail group={active} onBack={() => setOpenGroup(null)} onQueued={onQueued} />

  return <section className="space-y-3" aria-label={t("results.title")}>
    <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-[#8d9ab0]">
      <span>{t("results.summary", { total: response.total, eligible: response.eligible })}</span>
      <div className="flex items-center gap-3">
        <span>{t("results.expiry")}</span>
        <div className="flex rounded-[4px] border border-[#30405a] p-0.5" role="group" aria-label={t("results.viewMode")}>
          <ModeButton active={mode === "grid"} onClick={() => setMode("grid")} label={t("results.gridView")}><LayoutGrid size={13} /></ModeButton>
          <ModeButton active={mode === "list"} onClick={() => setMode("list")} label={t("results.listView")}><List size={13} /></ModeButton>
        </div>
      </div>
    </div>

    {mode === "list"
      ? <ResultList response={response} searched={searched} error={null} onQueued={onQueued} hideSummary />
      : <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {response.groups.map((group) => <PosterCard key={group.key} group={group} onOpen={setOpenGroup} />)}
        </div>}
  </section>
}

function ModeButton({ active, onClick, label, children }: {
  active: boolean; onClick: () => void; label: string; children: React.ReactNode
}) {
  return <button type="button" onClick={onClick} title={label} aria-label={label} aria-pressed={active}
    className={`rounded-[3px] px-2 py-1 transition ${active ? "bg-cyan-400/20 text-cyan-200" : "text-[#8d9ab0] hover:text-[#d4deeb]"}`}>
    {children}
  </button>
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-[6px] border border-dashed border-[#2b394f] bg-[#0d141f] px-4 py-10 text-center text-sm text-[#78869d]">{text}</div>
}
