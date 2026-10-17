import { Clapperboard } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { Scene } from "./planApi"
import { fileOf } from "./planLogic"

interface Props {
  scene: Scene | null
  base: string
  selected: string | null
  onSelect: (id: string) => void
}

/** Planen, unten: echte Shots der gewählten Szene als Leiste (Bearbeiten und „In Shots zerlegen“ folgen in 2b). */
export function StoryboardPanel({ scene, base, selected, onSelect }: Props) {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="storyboard">
      <div className="flex h-8 shrink-0 items-center gap-2 border-b border-[#2a364b] px-3 text-[11px] text-[#8d9ab0]">
        <span className="font-black uppercase tracking-[0.14em] text-[#68758a]">{t("storyboard")}</span>
        {scene && <span className="truncate">{scene.title || t("untitled")}</span>}
      </div>
      {!scene ? <p className="p-3 text-xs text-[#68758a]">{t("storyboard_pick_scene")}</p>
        : !scene.shots.length ? <p className="p-3 text-xs text-[#68758a]">{t("storyboard_no_shots")}</p>
          : (
            <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-3">
              {scene.shots.map((s, i) => {
                const img = fileOf(base, s.image_rel)
                return (
                  <button key={s.id} type="button" onClick={() => onSelect(s.id)} data-storyboard-shot={s.id} title={s.prompt}
                    className={`flex w-44 shrink-0 flex-col overflow-hidden rounded-[4px] border text-left ${s.id === selected ? "border-[#69d7ff]" : "border-[#2a364b]"} bg-[#111827]`}>
                    <span className="grid aspect-video place-items-center overflow-hidden bg-[#0d1420]">
                      {img ? <img src={fileUrl(img)} alt="" loading="lazy" className="h-full w-full object-cover" />
                        : <Clapperboard size={18} className="text-[#46617f]" />}
                    </span>
                    <span className="p-2 text-[11px]">
                      <span className="block font-bold text-[#e8eef8]">{t("shot", { n: i + 1 })} · {s.duration} s</span>
                      <span className="block truncate text-[#8d9ab0]">{s.prompt || (s.shot ? t(`cam.shot.${s.shot}`) : "")}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          )}
    </section>
  )
}
