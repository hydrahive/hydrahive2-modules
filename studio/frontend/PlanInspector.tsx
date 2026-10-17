import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { ElementForm } from "./ElementForm"
import { HeadForm } from "./HeadForm"
import { sceneOf } from "./planLogic"
import { SceneForm } from "./SceneForm"
import type { PlanState } from "./usePlan"

/** Planen, rechts: Formular des Gewählten. `key` mit `rev` setzt das Formular nach dem Speichern auf die frischen Daten. */
export function PlanInspector({ p, images }: { p: PlanState; images: LibraryItem[] }) {
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
  } else if (plan && sel?.kind === "shot") {
    const shot = sceneOf(plan, sel)?.shots.find((s) => s.id === sel.id)
    if (shot) {
      body = (
        <div className="mt-3 space-y-2 text-xs" data-plan-form="shot">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[#8d9ab0]">
            <dt>{t("f.camera")}</dt><dd className="text-right text-[#e8eef8]">{shot.shot ? t(`cam.shot.${shot.shot}`) : "–"}</dd>
            <dt>{t("length")}</dt><dd className="text-right text-[#e8eef8]">{shot.duration} s</dd>
            <dt>{t("f.status")}</dt><dd className="text-right text-[#e8eef8]">{t(`shot_status.${shot.status}`, { defaultValue: shot.status })}</dd>
          </dl>
          {shot.prompt && <p className="whitespace-pre-wrap rounded-[4px] bg-[#111827] p-2 text-[#c3ccdd]">{shot.prompt}</p>}
          <p className="text-[10px] leading-relaxed text-[#68758a]">{t("shots_soon")}</p>
        </div>
      )
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
