import { useTranslation } from "react-i18next"
import { Bluetooth, CalendarDays, Gauge, LayoutDashboard, Lightbulb, SlidersHorizontal } from "lucide-react"
import { TABS, type TabId } from "./tabs"

const ICONS: Record<TabId, typeof Gauge> = {
  overview: Gauge, program: CalendarDays, display: SlidersHorizontal, dashboard: LayoutDashboard, light: Lightbulb, bluetooth: Bluetooth,
}

/** Reiterleiste. Punkt: gelb = ungespeichert, rot = ungültig. Pfeiltasten wechseln (Tastatur). */
export function VitrineTabs({ active, dirty, invalid, onSelect }: {
  active: TabId; dirty: TabId[]; invalid: TabId[]; onSelect: (t: TabId) => void
}) {
  const { t } = useTranslation("vitrine")
  const move = (d: number) => onSelect(TABS[(TABS.indexOf(active) + d + TABS.length) % TABS.length])
  return (
    <nav role="tablist" aria-label={t("title")} className="flex gap-1 overflow-x-auto border-b border-[#2a364b]"
      onKeyDown={(e) => { if (e.key === "ArrowRight") move(1); if (e.key === "ArrowLeft") move(-1) }}>
      {TABS.map((id) => {
        const Icon = ICONS[id]
        const on = id === active
        const dot = invalid.includes(id) ? "bg-rose-400" : dirty.includes(id) ? "bg-amber-300" : null
        return (
          <button key={id} type="button" role="tab" aria-selected={on} tabIndex={on ? 0 : -1} onClick={() => onSelect(id)}
            data-tab={id}
            className={`relative flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm ${on
              ? "border-[#69d7ff] font-semibold text-[#e8eef8]" : "border-transparent text-[#8d9ab0] hover:text-[#c8d2df]"}`}>
            <Icon size={14} />{t(`tab_${id}`)}
            {dot && <span aria-label={t(invalid.includes(id) ? "tab_invalid" : "tab_dirty")} className={`h-1.5 w-1.5 rounded-full ${dot}`} />}
          </button>
        )
      })}
    </nav>
  )
}
