import { useState } from "react"
import { useTranslation } from "react-i18next"
import { formatDates, parseDates, type Rule } from "./rules"

const field = "w-full rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5 text-sm text-[#e8eef8]"
const label = "block text-xs text-[#9aa7bc]"

/** Felder der Feiertagsarten Adventssonntag, n-ter Wochentag und Termine je Jahr (Teil von RuleEditor). */
export function RuleFieldsExtra({ rule, errs, set }: { rule: Rule; errs: string[]; set: (p: Partial<Rule>) => void }) {
  const { t } = useTranslation("vitrine")
  const [text, setText] = useState(() => formatDates(rule.dates))
  const bad = (k: string) => (errs.includes(k) ? " border-rose-400/70" : "")

  if (rule.kind === "advent_sunday") return (
    <label className={label}>{t("advent_sunday_label")}
      <select className={field + bad("n")} value={rule.n ?? 1} onChange={(e) => set({ n: Number(e.target.value) })}>
        {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{t("advent_n", { n })}</option>)}
      </select>
    </label>
  )
  if (rule.kind === "nth_weekday") return <>
    <label className={label}>{t("nth_label")}
      <select className={field + bad("n")} value={rule.n ?? 1} onChange={(e) => set({ n: Number(e.target.value) })}>
        {[1, 2, 3, 4, 5, -1].map((n) => <option key={n} value={n}>{t(`nth.${n}`)}</option>)}
      </select>
    </label>
    <label className={label}>{t("weekday_label")}
      <select className={field + bad("weekday")} value={rule.weekday ?? 6} onChange={(e) => set({ weekday: Number(e.target.value) })}>
        {[0, 1, 2, 3, 4, 5, 6].map((w) => <option key={w} value={w}>{t(`weekday.${w}`)}</option>)}
      </select>
    </label>
    <label className={label}>{t("month_label")}
      <select className={field + bad("month")} value={rule.month ?? 5} onChange={(e) => set({ month: Number(e.target.value) })}>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => <option key={m} value={m}>{t(`month.${m}`)}</option>)}
      </select>
    </label>
    <label className={label}>{t("days_label")}
      <input type="number" min={1} max={31} className={field + bad("days")} value={rule.days ?? 1} onChange={(e) => set({ days: Number(e.target.value) })} />
    </label>
  </>
  if (rule.kind === "dates") return (
    <label className={label + " md:col-span-2"}>{t("dates_label")}
      <textarea rows={5} className={field + " font-mono" + bad("dates")} placeholder="2026-12-04 2026-12-12" value={text}
        onChange={(e) => { setText(e.target.value); set({ dates: parseDates(e.target.value) }) }} />
      <span className="mt-1 block text-[11px] text-[#9aa7bc]">{t("dates_hint")}</span>
    </label>
  )
  return null
}
