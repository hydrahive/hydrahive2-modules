import { Clapperboard, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { Plan, Selection } from "./planApi"
import { fileOf, sceneOf } from "./planLogic"

const frame = "flex aspect-video max-h-full w-full flex-col items-center justify-center gap-2 overflow-hidden rounded-[4px] border border-[#223048] bg-black p-4 text-center"

function Picture({ src, alt }: { src: string; alt: string }) {
  return <img src={fileUrl(src)} alt={alt} className="min-h-0 max-w-full flex-1 object-contain" />
}

/** Planen, Mitte: Bild des gewählten Shots, der Szene (erstes Shot-Bild) oder Referenzbild des Bausteins. */
export function PlanPreview({ plan, selection }: { plan: Plan | null; selection: Selection | null }) {
  const { t } = useTranslation("studio")
  if (!plan || !selection) return <div className={`${frame} text-xs text-[#68758a]`} data-plan-preview="none">{t("plan_pick")}</div>
  if (selection.kind === "head") {
    const h = plan.screenplay
    return (
      <div className={frame} data-plan-preview="head">
        <Clapperboard size={34} className="text-[#46617f]" />
        <span className="text-base font-black text-[#e8eef8]">{h.title || t("untitled")}</span>
        {h.logline && <span className="max-w-[80%] text-xs text-[#c3ccdd]">{h.logline}</span>}
        <span className="text-[10px] text-[#68758a]">{t("scene_count", { count: plan.scenes.length })} · {h.aspect_ratio}</span>
      </div>
    )
  }
  if (selection.kind === "element") {
    const el = plan.elements.find((e) => e.id === selection.id)
    const ref = fileOf(plan.base, el?.references[0])
    return (
      <div className={frame} data-plan-preview="element">
        {ref ? <Picture src={ref} alt={el?.name ?? ""} /> : <User size={42} className="text-[#46617f]" />}
        <span className="text-sm font-bold text-[#e8eef8]">{el?.name}</span>
      </div>
    )
  }
  const scene = sceneOf(plan, selection)
  const shot = selection.kind === "shot" ? scene?.shots.find((s) => s.id === selection.id) : scene?.shots.find((s) => s.image_rel)
  const img = fileOf(plan.base, shot?.image_rel)
  const vid = selection.kind === "shot" ? fileOf(plan.base, shot?.video_rel) : ""
  return (
    <div className={frame} data-plan-preview={selection.kind}>
      {vid ? <video key={vid} src={fileUrl(vid)} poster={img ? fileUrl(img) : undefined} controls preload="metadata"
        className="min-h-0 max-w-full flex-1 object-contain" data-plan-preview-video />
        : img ? <Picture src={img} alt={scene?.title ?? ""} /> : <Clapperboard size={34} className="text-[#46617f]" />}
      <span className="text-sm font-bold text-[#e8eef8]">{scene?.title || t("untitled")}</span>
      {selection.kind === "shot" && shot?.prompt && <span className="max-w-[80%] text-xs text-[#c3ccdd]">{shot.prompt}</span>}
      {selection.kind === "scene" && scene?.description && <span className="line-clamp-3 max-w-[80%] text-xs text-[#c3ccdd]">{scene.description}</span>}
    </div>
  )
}
