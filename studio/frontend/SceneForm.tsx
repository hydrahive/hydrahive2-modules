import { useState } from "react"
import { Plus, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CAMERA_KEYS, type Plan, type PlanElement, type Scene } from "./planApi"
import { Field, FormActions, Label, fieldCls } from "./formParts"

interface Props {
  scene: Scene
  elements: PlanElement[]
  presets: Plan["presets"]
  busy: boolean
  onSave: (s: Partial<Scene>) => void
  onDelete: () => void
}

/** Planen, rechts: eine Szene (Ort, Zeit, Beschreibung, Kamera, Bausteine, Dialoge). Shots folgen in 2b. */
export function SceneForm({ scene, elements, presets, busy, onSave, onDelete }: Props) {
  const { t } = useTranslation("studio")
  const [s, setS] = useState(scene)
  const dirty = JSON.stringify(s) !== JSON.stringify(scene)
  const set = <K extends keyof Scene>(k: K, v: Scene[K]) => setS((x) => ({ ...x, [k]: v }))
  const toggle = (id: string) => set("element_ids", s.element_ids.includes(id) ? s.element_ids.filter((x) => x !== id) : [...s.element_ids, id])
  const line = (i: number, patch: Partial<Scene["dialogues"][number]>) =>
    set("dialogues", s.dialogues.map((d, j) => (j === i ? { ...d, ...patch } : d)))
  return (
    <div className="mt-3 space-y-3 text-xs" data-plan-form="scene">
      <Field name="title" label={t("f.title")} value={s.title} max={200} onChange={(v) => set("title", v)} />
      <div className="grid grid-cols-2 gap-2">
        <Field name="location" label={t("f.location")} value={s.location} max={200} onChange={(v) => set("location", v)} />
        <Field name="time_of_day" label={t("f.time_of_day")} value={s.time_of_day} max={50} onChange={(v) => set("time_of_day", v)} />
      </div>
      <Field name="description" label={t("f.description")} value={s.description} max={4000} rows={4} onChange={(v) => set("description", v)} />
      <fieldset className="grid grid-cols-2 gap-2">
        <legend className="col-span-2"><Label>{t("f.camera")}</Label></legend>
        {CAMERA_KEYS.map((k) => (
          <label key={k} className="block" data-scene-camera={k}>
            <span className="text-[10px] text-[#9aa7bc]">{t(`cam_group.${k}`)}</span>
            <select value={s.camera[k] ?? ""} className={fieldCls}
              onChange={(e) => { const { [k]: _old, ...rest } = s.camera; set("camera", e.target.value ? { ...rest, [k]: e.target.value } : rest) }}>
              <option value="">{t("cam_any")}</option>
              {(presets[k] ?? []).map((v) => <option key={v} value={v}>{t(`cam.${k}.${v}`)}</option>)}
            </select>
          </label>
        ))}
      </fieldset>
      <div>
        <Label>{t("elements")}</Label>
        {!elements.length && <p className="mt-1 text-[11px] text-[#9aa7bc]">{t("no_elements")}</p>}
        <div className="mt-1 flex flex-wrap gap-1">
          {elements.map((e) => (
            <label key={e.id} className="flex items-center gap-1 rounded-full bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-0.5 text-[11px] text-[#c3ccdd]">
              <input type="checkbox" checked={s.element_ids.includes(e.id)} onChange={() => toggle(e.id)} data-scene-element={e.id} /> {e.name}
            </label>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        <Label>{t("f.dialogues")}</Label>
        {s.dialogues.map((d, i) => (
          <div key={i} className="space-y-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2" data-scene-dialogue={i}>
            <div className="flex gap-1">
              <select value={d.element_id} onChange={(e) => line(i, { element_id: e.target.value })} className={`${fieldCls} mt-0`} aria-label={t("f.speaker")}>
                <option value="">{t("f.narrator")}</option>
                {elements.filter((e) => e.kind === "character").map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
              <button type="button" onClick={() => set("dialogues", s.dialogues.filter((_, j) => j !== i))} aria-label={t("delete")}
                className="rounded p-1 text-[#9aa7bc] hover:text-[#ff6b8a]"><X size={12} /></button>
            </div>
            <textarea rows={2} maxLength={2000} value={d.line} onChange={(e) => line(i, { line: e.target.value })} className={fieldCls} aria-label={t("f.line")} />
            <input value={d.emotion} maxLength={50} placeholder={t("f.emotion")} onChange={(e) => line(i, { emotion: e.target.value })} className={fieldCls} />
          </div>
        ))}
        <button type="button" onClick={() => set("dialogues", [...s.dialogues, { element_id: "", line: "", emotion: "" }])} disabled={s.dialogues.length >= 100}
          className="flex items-center gap-1 text-[11px] text-[#9aa7bc] hover:text-[#e8eef8]" data-scene-add-dialogue><Plus size={12} /> {t("f.add_dialogue")}</button>
      </div>
      <FormActions busy={busy} dirty={dirty} onDelete={onDelete}
        onSave={() => onSave({ title: s.title, description: s.description, location: s.location, time_of_day: s.time_of_day,
          element_ids: s.element_ids, dialogues: s.dialogues, camera: s.camera })} />
    </div>
  )
}
