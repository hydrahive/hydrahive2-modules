import { ChevronLeft, ChevronRight, Clapperboard, Film, Loader2, Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { Scene } from "./planApi"
import { fileOf, sceneDuration } from "./planLogic"

interface Props {
  scene: Scene | null
  base: string
  selected: string | null
  busy: "decompose" | null
  runningShots?: string[]
  onSelect: (id: string) => void
  onAdd: () => void
  onMove: (id: string, dir: -1 | 1) => void
  onDecompose: () => void
}

const arrow = "rounded p-0.5 text-[#68758a] hover:bg-[#1c2940] hover:text-[#e8eef8] disabled:opacity-30 disabled:hover:bg-transparent"

/** Planen, unten: Shots der gewählten Szene – anklicken, sortieren, hinzufügen, per Regie-Agent zerlegen. */
export function StoryboardPanel({ scene, base, selected, busy, runningShots = [], onSelect, onAdd, onMove, onDecompose }: Props) {
  const { t } = useTranslation("studio")
  const running = busy === "decompose"
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="storyboard">
      <div className="flex h-8 shrink-0 items-center gap-2 border-b border-[#2a364b] px-3 text-[11px] text-[#8d9ab0]">
        <span className="font-black uppercase tracking-[0.14em] text-[#68758a]">{t("storyboard")}</span>
        {scene && <span className="truncate">{scene.title || t("untitled")}</span>}
        {scene && scene.shots.length > 0 && <span className="shrink-0 text-[#68758a]" data-storyboard-duration>{t("scene_duration", { seconds: sceneDuration(scene) })}</span>}
        <span className="ml-auto" />
        {scene && (
          <button type="button" onClick={onDecompose} disabled={running} data-storyboard-decompose title={t("decompose_hint")}
            className="flex shrink-0 items-center gap-1.5 rounded-[4px] border border-[#46617f] px-2 py-0.5 font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
            {running ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} {running ? t("decompose_running") : t("decompose")}
          </button>
        )}
      </div>
      {!scene ? <p className="p-3 text-xs text-[#68758a]">{t("storyboard_pick_scene")}</p> : (
        <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-3">
          {!scene.shots.length && <p className="max-w-sm self-center text-xs leading-relaxed text-[#68758a]">{t("storyboard_no_shots")}</p>}
          {scene.shots.map((s, i) => {
            const img = fileOf(base, s.image_rel)
            return (
              <div key={s.id} className={`flex w-44 shrink-0 flex-col overflow-hidden rounded-[4px] border ${s.id === selected ? "border-[#69d7ff]" : "border-[#2a364b]"} bg-[#111827]`}>
                <button type="button" onClick={() => onSelect(s.id)} data-storyboard-shot={s.id} title={s.prompt} className="flex flex-col text-left">
                  <span className="relative grid aspect-video place-items-center overflow-hidden bg-[#0d1420]">
                    {img ? <img src={fileUrl(img)} alt="" loading="lazy" className="h-full w-full object-cover" />
                      : <Clapperboard size={18} className="text-[#46617f]" />}
                    {s.video_rel && (
                      <span className="absolute bottom-1 right-1 rounded bg-black/70 p-0.5 text-[#69d7ff]" data-storyboard-video={s.id} title={t("video")}>
                        <Film size={12} />
                      </span>
                    )}
                    {runningShots.includes(s.id) && (
                      <span className="absolute inset-0 grid place-items-center bg-black/55" data-storyboard-running={s.id} title={t("job_running")}>
                        <Loader2 size={18} className="animate-spin text-[#69d7ff]" />
                      </span>
                    )}
                  </span>
                  <span className="px-2 pt-1.5 text-[11px]">
                    <span className="block font-bold text-[#e8eef8]">{t("shot", { n: i + 1 })} · {s.duration} s</span>
                    <span className="block truncate text-[#8d9ab0]">{s.prompt || (s.shot ? t(`cam.shot.${s.shot}`) : "")}</span>
                  </span>
                </button>
                <span className="flex justify-end gap-0.5 px-1 pb-1">
                  <button type="button" onClick={() => onMove(s.id, -1)} disabled={i === 0} data-storyboard-move={`${s.id}:-1`} aria-label={t("move_left")} className={arrow}><ChevronLeft size={13} /></button>
                  <button type="button" onClick={() => onMove(s.id, 1)} disabled={i === scene.shots.length - 1} data-storyboard-move={`${s.id}:1`} aria-label={t("move_right")} className={arrow}><ChevronRight size={13} /></button>
                </span>
              </div>
            )
          })}
          <button type="button" onClick={onAdd} disabled={running} data-storyboard-add title={t("add_shot")} aria-label={t("add_shot")}
            className="grid w-24 shrink-0 place-items-center rounded-[4px] border border-dashed border-[#2a364b] text-[#68758a] hover:text-[#e8eef8] disabled:opacity-40">
            <Plus size={18} />
          </button>
        </div>
      )}
    </section>
  )
}
