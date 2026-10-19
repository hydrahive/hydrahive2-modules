import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowDown, ArrowUp, LayoutDashboard } from "lucide-react"
import { vitrineApi, type VitrineConfig } from "./api"
import { DashboardAreaOptions } from "./DashboardAreaOptions"
import { type AreaId, byPage, layoutErrors, moveInPage, normalizeDashboard, toggleIn } from "./dashLayout"

const btn = "rounded-[4px] border border-[#2a364b] p-1 text-[#c8d2df] disabled:opacity-30"

/** „Statuszentrale anpassen“ (S4): Bereiche an/aus, Reihenfolge, wenige Einstellungen je Bereich. Speichern wirkt sofort. */
export function DashboardCard({ config, onChange }: { config: VitrineConfig; onChange: (c: VitrineConfig) => void }) {
  const { t } = useTranslation("vitrine")
  const d = normalizeDashboard(config.dashboard)
  const set = (patch: Partial<typeof d>) => onChange({ ...config, dashboard: { ...d, ...patch } })
  const errs = layoutErrors(d)
  const [rooms, setRooms] = useState<{ rooms: string[]; available: boolean } | null>(null)
  useEffect(() => { vitrineApi.homeRooms().then(setRooms).catch(() => setRooms({ rooms: [], available: false })) }, [])
  const mining = (id: AreaId) => id === "mining" && d.mining_in_machine
  return (
    <section className="space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><LayoutDashboard size={15} className="text-[#69d7ff]" />{t("dash_title")}</h2>
      <p className="text-xs text-[#718097]">{t("dash_hint")}</p>
      <ol className="space-y-2">
        {byPage(d).map((id, i, list) => {
          const on = !d.hidden.includes(id)
          const page = d.pages[id] ?? 1
          const firstOfPage = i === 0 || (d.pages[list[i - 1]] ?? 1) !== page
          const lastOfPage = i === list.length - 1 || (d.pages[list[i + 1]] ?? 1) !== page
          return (
            <li key={id} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2">
              {firstOfPage && <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-[#69d7ff]">{t("dash_page", { n: page })}</p>}
              <div className="flex items-center gap-2">
                <button type="button" className={btn} disabled={firstOfPage} onClick={() => set({ order: moveInPage(d, id, -1) })}
                  aria-label={t("dash_up")} title={t("dash_up")}><ArrowUp size={13} /></button>
                <button type="button" className={btn} disabled={lastOfPage} onClick={() => set({ order: moveInPage(d, id, 1) })}
                  aria-label={t("dash_down")} title={t("dash_down")}><ArrowDown size={13} /></button>
                <label className="flex flex-1 items-center gap-2 text-sm text-[#e8eef8]">
                  <input type="checkbox" checked={on} disabled={mining(id)} onChange={() => set({ hidden: toggleIn(d.hidden, id) })} />
                  {t(`dash_area.${id}`)}
                  {mining(id) && <span className="text-xs text-[#718097]">({t("dash_mining_shown_in_machine")})</span>}
                </label>
                <select value={page} aria-label={t("dash_page_label")} title={t("dash_page_label")}
                  className={`rounded-[4px] border bg-[#0d1420] px-1 py-0.5 text-xs text-[#e8eef8] ${errs.includes("pages") ? "border-rose-400" : "border-[#2a364b]"}`}
                  onChange={(e) => set({ pages: { ...d.pages, [id]: Number(e.target.value) } })}>
                  {[1, 2, 3].map((n) => <option key={n} value={n}>{t("dash_page", { n })}</option>)}
                </select>
              </div>
              {on && <div className="mt-2 pl-16"><DashboardAreaOptions id={id} d={d} errs={errs} rooms={rooms} set={set} /></div>}
            </li>
          )
        })}
      </ol>
      {errs.length > 0 && <p className="text-xs text-rose-300">{t("dash_invalid")}</p>}
    </section>
  )
}
