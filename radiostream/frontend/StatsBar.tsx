import { useTranslation } from "react-i18next"
import type { Stats } from "./api"
import { fmtTotal } from "./logic"

const n = (v: number) => v.toLocaleString("de-DE")

/** Zahlen oben: Titel, Künstler, Spielzeit, Fehlendes/Unlesbares. */
export function StatsBar({ stats }: { stats: Stats }) {
  const { t } = useTranslation("radiostream")
  const total = fmtTotal(stats.duration_s)
  return (
    <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1 text-sm text-[#c8d2df]" data-radiostream-stats>
      <span><b className="text-lg text-[#e8eef8]">{n(stats.tracks)}</b> {t("stats.tracks")}</span>
      <span><b className="text-lg text-[#e8eef8]">{n(stats.artists)}</b> {t("stats.artists")}</span>
      <span>{t("stats.days", total)}</span>
      {stats.missing > 0 && <span className="text-amber-300">{t("stats.missing", { count: stats.missing })}</span>}
      {stats.errors > 0 && <span className="text-amber-300">{t("stats.errors", { count: stats.errors })}</span>}
    </div>
  )
}
