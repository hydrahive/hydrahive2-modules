import { useTranslation } from "react-i18next"
import type { Outages } from "./api"
import { dayRows, duration, type Speedtest } from "./logic"
import { BOX, H2, MUTED } from "./ui"
import { dayLabel, when } from "./when"

function DayList({ title, perDay }: { title: string; perDay: Record<string, number> }) {
  const { t, i18n } = useTranslation("network")
  const rows = dayRows(perDay)
  return (
    <section className={BOX}>
      <h2 className={H2}>{title}</h2>
      {rows.length === 0 ? <p className={MUTED}>{t("outages.none")}</p> : (
        <ul className="space-y-1 text-sm">
          {rows.map((r) => (
            <li key={r.day} className="flex justify-between gap-3">
              <span className="text-[#c8d2df]">{dayLabel(r.day, i18n.language)}</span>
              <span className={r.seconds >= 3600 ? "text-rose-300" : "text-[#e8eef8]"}>{duration(r.seconds, t)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** Störungen: je Tag, Liste aller Zeiträume, Geschwindigkeitstests (ohne Laden – gut testbar). */
export function OutagesView({ d, speedtests, planUp }: { d: Outages; speedtests: Speedtest[]; planUp: number | null }) {
  const { t, i18n } = useTranslation("network")
  const items = d.items.filter((o) => o.kind !== "blip" || o.end - o.start >= 10)
  return (
    <div className="space-y-4" data-network-outages>
      <div className="grid gap-4 md:grid-cols-2">
        <DayList title={t("outages.per_day")} perDay={d.per_day} />
        <DayList title={t("outages.per_day_cable")} perDay={d.per_day_cable} />
      </div>
      <section className={BOX}>
        <h2 className={H2}>{t("outages.speedtests")}</h2>
        {speedtests.length === 0 ? <p className={MUTED}>{t("speed.none")}</p> : (
          <ul className="space-y-1 text-sm">
            {[...speedtests].reverse().map((s) => (
              <li key={`${s.source}-${s.ts}`} className="flex justify-between gap-3">
                <span className="text-[#c8d2df]">{when(s.ts, i18n.language)}</span>
                <span className={planUp && s.up_mbit !== null && s.up_mbit < planUp / 2 ? "text-rose-300" : "text-[#e8eef8]"}>
                  {t("outages.speed_row", { down: s.down_mbit ?? "–", up: s.up_mbit ?? "–" })}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className={BOX}>
        <h2 className={H2}>{t("outages.list")}</h2>
        {items.length === 0 ? <p className={MUTED}>{t("outages.none")}</p> : (
          <ul className="divide-y divide-[rgb(var(--hh-s-rand,42_54_75))] text-sm">
            {items.map((o) => (
              <li key={`${o.kind}-${o.source}-${o.start}`} className="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                <span className="text-[#e8eef8]">{t(`outages.kind.${o.kind}`)}</span>
                <span className="text-[#c8d2df]">{t("outages.from_to", { from: when(o.start, i18n.language), to: when(o.end, i18n.language) })}</span>
                <span className="text-[#e8eef8]">{duration(o.end - o.start, t)}</span>
                <span className="text-xs text-[#c8d2df]">{t(`outages.source.${o.source}`)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
