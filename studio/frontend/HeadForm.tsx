import { useState } from "react"
import { useTranslation } from "react-i18next"
import { ASPECTS, LANGUAGES, MODEL_KEYS, type Head } from "./planApi"
import { paletteFromText } from "./planLogic"
import { Field, FormActions, Label, fieldCls } from "./formParts"
import { ModelPick } from "./ModelPick"
import type { Catalog, ModelKind } from "./modelCatalog"

interface Props {
  head: Head
  busy: boolean
  onSave: (h: Partial<Head>) => void
  catalogs?: Partial<Record<ModelKind, Catalog | null>>
}

/** Planen, rechts: Drehbuch-Kopf (Titel, Kurzbeschreibung, Format, Standard-Dauer, Modelle, Look). */
export function HeadForm({ head, busy, onSave, catalogs = {} }: Props) {
  const { t } = useTranslation("studio")
  const [h, setH] = useState(head)
  const [palette, setPalette] = useState(head.look.palette.join(", "))
  const dirty = JSON.stringify(h) !== JSON.stringify(head) || palette !== head.look.palette.join(", ")
  const set = <K extends keyof Head>(k: K, v: Head[K]) => setH((x) => ({ ...x, [k]: v }))
  return (
    <div className="mt-3 space-y-3 text-xs" data-plan-form="head">
      <Field name="title" label={t("f.title")} value={h.title} max={200} onChange={(v) => set("title", v)} />
      <Field name="logline" label={t("f.logline")} value={h.logline} max={500} rows={2} onChange={(v) => set("logline", v)} />
      <Field name="description" label={t("f.description")} value={h.description} max={4000} rows={4} onChange={(v) => set("description", v)} />
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><Label>{t("f.aspect")}</Label>
          <select value={h.aspect_ratio} onChange={(e) => set("aspect_ratio", e.target.value)} className={fieldCls}>
            {ASPECTS.map((a) => <option key={a} value={a} data-head-aspect={a}>{a}</option>)}
          </select>
        </label>
        <label className="block"><Label>{t("f.duration")}</Label>
          <input type="number" min={1} max={60} value={h.default_duration} className={fieldCls}
            onChange={(e) => set("default_duration", Math.max(1, Math.min(60, Number(e.target.value) || 1)))} />
        </label>
      </div>
      <label className="block"><Label>{t("sub_language")}</Label>
        <select value={h.language ?? "de"} onChange={(e) => set("language", e.target.value)} className={fieldCls}>
          {LANGUAGES.map((l) => <option key={l} value={l} data-head-language={l}>{t(`lang.${l}`)}</option>)}
        </select>
      </label>
      <fieldset className="space-y-2">
        <legend><Label>{t("f.models")}</Label></legend>
        {MODEL_KEYS.map((k) => (
          <ModelPick key={k} kind={k} value={h.models[k]} catalog={catalogs[k] ?? null}
            onChange={(v) => set("models", { ...h.models, [k]: v })} />
        ))}
        <p className="text-[10px] leading-relaxed text-[#68758a]">{t("f.models_hint")}</p>
      </fieldset>
      <Field name="style" label={t("f.style")} value={h.look.style} max={2000} rows={2} onChange={(v) => set("look", { ...h.look, style: v })} />
      <Field name="palette" label={t("f.palette")} value={palette} max={300} onChange={setPalette} />
      <FormActions busy={busy} dirty={dirty}
        onSave={() => onSave({ ...h, look: { ...h.look, palette: paletteFromText(palette) } })} />
    </div>
  )
}
