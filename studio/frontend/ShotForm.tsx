import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Job, PlanElement, Shot } from "./planApi"
import { ShotImage } from "./ShotImage"
import { Field, FormActions, Label, fieldCls } from "./formParts"

interface Props {
  shot: Shot
  index: number
  elements: PlanElement[]
  sceneElementIds: string[]
  presets: string[]
  busy: boolean
  onSave: (s: Partial<Shot>) => void
  onDelete: () => void
  base?: string
  job?: Job | null
  onGenerate?: () => void
  onChoose?: (rel: string) => void
}

/** Planen, rechts: ein Shot (Kamera, Beschreibung, Bausteine der Szene, Dauer). Status und Medien ändert das Erzeugen. */
export function ShotForm({ shot, index, elements, sceneElementIds, presets, busy, onSave, onDelete, base = "", job = null, onGenerate, onChoose }: Props) {
  const { t } = useTranslation("studio")
  const [s, setS] = useState(shot)
  const dirty = JSON.stringify(s) !== JSON.stringify(shot)
  const inScene = elements.filter((e) => sceneElementIds.includes(e.id))
  const toggle = (id: string) => setS((x) => ({ ...x, element_ids: x.element_ids.includes(id) ? x.element_ids.filter((y) => y !== id) : [...x.element_ids, id] }))
  return (
    <div className="mt-3 space-y-3 text-xs" data-plan-form="shot">
      <p className="font-bold text-[#e8eef8]">{t("shot", { n: index + 1 })}</p>
      {onGenerate && onChoose && <ShotImage shot={shot} base={base} job={job} onGenerate={onGenerate} onChoose={onChoose} />}
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><Label>{t("f.camera")}</Label>
          <select value={s.shot} onChange={(e) => setS({ ...s, shot: e.target.value })} className={fieldCls}>
            <option value="">{t("cam_any")}</option>
            {presets.map((v) => <option key={v} value={v}>{t(`cam.shot.${v}`)}</option>)}
          </select>
        </label>
        <label className="block"><Label>{t("f.shot_duration")}</Label>
          <input type="number" min={1} max={60} value={s.duration} className={fieldCls}
            onChange={(e) => setS({ ...s, duration: Math.max(1, Math.min(60, Number(e.target.value) || 1)) })} />
        </label>
      </div>
      <Field name="prompt" label={t("f.shot_prompt")} value={s.prompt} max={2000} rows={5} onChange={(v) => setS({ ...s, prompt: v })} />
      <div>
        <Label>{t("elements")}</Label>
        {!inScene.length && <p className="mt-1 text-[11px] text-[#68758a]">{t("shot_no_elements")}</p>}
        <div className="mt-1 flex flex-wrap gap-1">
          {inScene.map((e) => (
            <label key={e.id} className="flex items-center gap-1 rounded-full bg-[#111827] px-2 py-0.5 text-[11px] text-[#c3ccdd]">
              <input type="checkbox" checked={s.element_ids.includes(e.id)} onChange={() => toggle(e.id)} data-shot-element={e.id} /> {e.name}
            </label>
          ))}
        </div>
      </div>
      <p className="text-[11px] text-[#8d9ab0]">{t("f.status")}: <span className="text-[#e8eef8]">{t(`shot_status.${shot.status}`, { defaultValue: shot.status })}</span></p>
      <FormActions busy={busy} dirty={dirty} onDelete={onDelete}
        onSave={() => onSave({ shot: s.shot, prompt: s.prompt, element_ids: s.element_ids, duration: s.duration })} />
    </div>
  )
}
