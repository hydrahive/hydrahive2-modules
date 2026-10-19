import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowDown, ArrowUp, LayoutDashboard } from "lucide-react"
import { vitrineApi, type VitrineConfig } from "./api"
import { DashboardAreaOptions } from "./DashboardAreaOptions"
import { type AreaId, layoutErrors, moveArea, normalizeDashboard, toggleIn } from "./dashLayout"

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
        {d.order.map((id, i) => {
          const on = !d.hidden.includes(id)
          return (
            <li key={id} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2">
              <div className="flex items-center gap-2">
                <button type="button" className={btn} disabled={i === 0} onClick={() => set({ order: moveArea(d.order, id, -1) })}
                  aria-label={t("dash_up")} title={t("dash_up")}><ArrowUp size={13} /></button>
                <button type="button" className={btn} disabled={i === d.order.length - 1} onClick={() => set({ order: moveArea(d.order, id, 1) })}
                  aria-label={t("dash_down")} title={t("dash_down")}><ArrowDown size={13} /></button>
                <label className="flex flex-1 items-center gap-2 text-sm text-[#e8eef8]">
                  <input type="checkbox" checked={on} disabled={mining(id)} onChange={() => set({ hidden: toggleIn(d.hidden, id) })} />
                  {t(`dash_area.${id}`)}
                  {mining(id) && <span className="text-xs text-[#718097]">({t("dash_mining_shown_in_machine")})</span>}
                </label>
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
