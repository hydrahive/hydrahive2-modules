import { AlertTriangle, ArrowRight, Clapperboard, Film, Image as ImageIcon, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { Job, Plan } from "./planApi"
import { fileOf } from "./planLogic"
import { shotCounts, shotState, type ShotState } from "./shotListLogic"

interface Props {
  plan: Plan | null
  jobs: Job[]
  selected: string | null
  onSelect: (sceneId: string, shotId: string) => void
  onPlan: () => void
}

const ICON: Record<ShotState, React.ReactNode> = {
  none: <Clapperboard size={11} />, image: <ImageIcon size={11} />, video: <Film size={11} />,
  running: <Loader2 size={11} className="animate-spin" />, failed: <AlertTriangle size={11} />,
}
const COLOR: Record<ShotState, string> = {
  none: "text-[#9aa7bc]", image: "text-[#c3ccdd]", video: "text-[#69d7ff]", running: "text-[#ffb86b]", failed: "text-[#ff6b8a]",
}

/** Reiter „Erzeugen“, links: alle Shots aller Szenen mit Stand – anklicken, rechts erzeugen. */
export function ShotList({ plan, jobs, selected, onSelect, onPlan }: Props) {
  const { t } = useTranslation("studio")
  const c = shotCounts(plan)
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="shots">
      <div className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2">
        <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("gen_shots")}</h2>
        {c.total > 0 && <p className="mt-0.5 text-[11px] text-[#9aa7bc]" data-gen-counts>{t("gen_counts", { image: c.image, video: c.video, total: c.total })}</p>}
      </div>
      {!c.total ? (
        <div className="space-y-2 p-3 text-xs text-[#9aa7bc]">
          <p className="leading-relaxed">{t("gen_no_shots")}</p>
          <button type="button" onClick={onPlan} data-gen-to-plan
            className="flex items-center gap-1.5 rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] px-2 py-1 font-bold text-[#69d7ff] hover:bg-[#1c2940]">
            {t("gen_to_plan")} <ArrowRight size={12} />
          </button>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {plan?.scenes.filter((s) => s.shots.length).map((scene) => (
            <div key={scene.id} className="mb-2" data-gen-scene={scene.id}>
              <p className="truncate px-1 pb-1 text-[10px] font-black uppercase tracking-[0.1em] text-[#9aa7bc]">{scene.title || t("untitled")}</p>
              {scene.shots.map((shot, i) => {
                const state = shotState(shot, jobs)
                const img = fileOf(plan.base, shot.image_rel)
                const active = shot.id === selected
                return (
                  <button key={shot.id} type="button" onClick={() => onSelect(scene.id, shot.id)} data-gen-shot={shot.id} data-gen-state={state}
                    aria-pressed={active} title={shot.prompt}
                    className={`mb-1 flex w-full items-center gap-2 rounded-[4px] border px-1.5 py-1 text-left ${active ? "border-[#69d7ff] bg-[#1c2940]" : "border-transparent hover:bg-[rgb(var(--hh-s-hebung,17_24_39))]"}`}>
                    <span className="grid h-8 w-14 shrink-0 place-items-center overflow-hidden rounded-[3px] bg-[rgb(var(--hh-s-tief,13_20_32))]">
                      {img ? <img src={fileUrl(img)} alt="" loading="lazy" className="h-full w-full object-cover" /> : <Clapperboard size={13} className="text-[#46617f]" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[11px] font-bold text-[#e8eef8]">{t("shot", { n: i + 1 })}</span>
                      <span className="block truncate text-[10px] text-[#9aa7bc]">{shot.prompt || t("gen_no_prompt")}</span>
                    </span>
                    <span className={`flex shrink-0 items-center gap-1 text-[10px] ${COLOR[state]}`}>{ICON[state]} {t(`gen_state.${state}`)}</span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
