import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { ElementForm } from "./ElementForm"
import { HeadForm } from "./HeadForm"
import { sceneOf } from "./planLogic"
import { SceneForm } from "./SceneForm"
import { ShotForm } from "./ShotForm"
import type { PlanState } from "./usePlan"
import type { ShotsState } from "./useShots"
import type { Job } from "./planApi"
import { jobFor } from "./jobLogic"

/** Planen, rechts: Formular des Gewählten. `key` mit `rev` setzt das Formular nach dem Speichern auf die frischen Daten. */
export function PlanInspector({ p, shots, images, jobs = [] }: { p: PlanState; shots?: ShotsState; images: LibraryItem[]; jobs?: Job[] }) {
  const { t } = useTranslation("studio")
  const { plan, selection: sel } = p
  let body: React.ReactNode = <p className="mt-3 text-xs text-[#68758a]">{t("nothing_selected")}</p>
  if (plan && sel?.kind === "head") {
    body = <HeadForm key={`head-${p.rev}`} head={plan.screenplay} busy={p.busy} onSave={(h) => void p.saveHead(h)} />
  } else if (plan && sel?.kind === "scene") {
    const scene = sceneOf(plan, sel)
    if (scene) {
      body = <SceneForm key={`${scene.id}-${p.rev}`} scene={scene} elements={plan.elements} presets={plan.presets} busy={p.busy}
        onSave={(s) => void p.saveScene(scene.id, s)} onDelete={() => p.setDialog({ kind: "delete", target: "scene", id: scene.id, name: scene.title || t("untitled") })} />
    }
  } else if (plan && sel?.kind === "element") {
    const el = plan.elements.find((e) => e.id === sel.id)
    if (el) {
      body = <ElementForm key={`${el.id}-${p.rev}`} element={el} base={plan.base} images={images} busy={p.busy}
        onSave={(e) => void p.saveElement(el.id, e)} onDelete={() => p.setDialog({ kind: "delete", target: "element", id: el.id, name: el.name })} />
    }
  } else if (plan && sel?.kind === "shot" && shots) {
    const scene = sceneOf(plan, sel)
    const index = scene?.shots.findIndex((s) => s.id === sel.id) ?? -1
    const shot = index >= 0 ? scene?.shots[index] : undefined
    if (scene && shot) {
      body = <ShotForm key={`${shot.id}-${p.rev}`} shot={shot} index={index} elements={plan.elements} sceneElementIds={scene.element_ids}
        presets={plan.presets.shot ?? []} busy={p.busy} onSave={(d) => void shots.save(shot.id, d)} onDelete={() => shots.remove(shot.id, index)}
        base={plan.base} job={jobFor(jobs, shot.id)} onGenerate={() => void shots.generateImage(shot.id)}
        onChoose={(rel) => void shots.chooseVariant(shot.id, rel)} />
    }
  }
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("properties")}</h2>
      {p.error && <p className="mt-2 rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2 py-1.5 text-xs text-[#ff6b8a]" data-plan-error>{p.error}</p>}
      {body}
    </section>
  )
}
