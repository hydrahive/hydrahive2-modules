import { Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_TRACKS } from "./demoData"

/** Arbeitsbereich „Planen“: Szenen/Shots als Leiste statt Zeitleiste (Storyboard, Attrappe). */
export function StoryboardPanel({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { t } = useTranslation("studio")
  const shots = DEMO_TRACKS.find((tr) => tr.kind === "video")?.clips ?? []
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="storyboard">
      <div className="flex h-8 shrink-0 items-center gap-2 border-b border-[#2a364b] px-3 text-[11px] text-[#8d9ab0]">
        <span className="font-black uppercase tracking-[0.14em] text-[#68758a]">{t("storyboard")}</span>
        <span>{t("act", { n: 1 })} · {t("scene", { n: 1 })}</span>
        <span className="ml-auto" />
        <span className="shrink-0 rounded-full border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-2 py-0.5 text-[10px] text-[#ffb86b]" data-studio-demo-badge>{t("demo_badge")}</span>
      </div>
      <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-3">
        {shots.map((s, i) => (
          <button key={s.id} type="button" onClick={() => onSelect(s.id)} data-storyboard-shot={s.id}
            className={`flex w-44 shrink-0 flex-col overflow-hidden rounded-[4px] border text-left ${s.id === selected ? "border-[#69d7ff]" : "border-[#2a364b]"} bg-[#111827]`}>
            <span className={`grid aspect-video place-items-center ${s.placeholder ? "border-b border-dashed border-[#ffb86b] text-[#ffb86b]" : "bg-gradient-to-br from-[#2f6aa8] to-[#0d1420]"}`}>
              {s.placeholder && <Sparkles size={18} />}
            </span>
            <span className="p-2 text-[11px]">
              <span className="block font-bold text-[#e8eef8]">{t("shot", { n: i + 1 })} · {s.length} s</span>
              <span className="block truncate text-[#8d9ab0]">{s.label}</span>
            </span>
          </button>
        ))}
        <button type="button" className="grid w-28 shrink-0 place-items-center rounded-[4px] border border-dashed border-[#2a364b] text-[#68758a] hover:text-[#e8eef8]">
          <Plus size={18} />
        </button>
      </div>
    </section>
  )
}
