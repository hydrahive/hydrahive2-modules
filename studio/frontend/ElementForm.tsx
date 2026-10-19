import { useState } from "react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { LibraryItem } from "./api"
import { ELEMENT_KINDS, type PlanElement } from "./planApi"
import { paletteFromText } from "./planLogic"
import { Field, FormActions, Label, fieldCls } from "./formParts"
import { ElementPhoto } from "./ElementPhoto"
import { pendingElement } from "./uploadLogic"

interface Props {
  element: PlanElement
  base: string
  images: LibraryItem[]
  busy: boolean
  onSave: (e: Partial<PlanElement>) => void
  onDelete: () => void
  /** Eigenes Bild als Referenz hochladen (7a); `pending`: noch nicht gespeicherte Felder, die vorher gespeichert werden */
  onUploadReference?: (file: File, pending: Partial<PlanElement> | null) => void
  uploading?: boolean
  /** C2: Beschreibung + Aussehen aus dem Foto (Bild-KI); `pending` wird vorher gespeichert */
  onDescribe?: (pending: Partial<PlanElement> | null) => void
  describing?: boolean
}

/** Planen, rechts: Baustein (Figur, Ort, Gegenstand). Ganz oben die Vorlage-Fotos (C2), darunter die Angaben; Fotos aus
 *  der Bibliothek gehen auch (höchstens 8). */
export function ElementForm({ element, base, images, busy, onSave, onDelete, onUploadReference, uploading = false, onDescribe,
  describing = false }: Props) {
  const { t } = useTranslation("studio")
  const [e, setE] = useState(element)
  const [palette, setPalette] = useState(element.palette.join(", "))
  const dirty = JSON.stringify(e) !== JSON.stringify(element) || palette !== element.palette.join(", ")
  const set = <K extends keyof PlanElement>(k: K, v: PlanElement[K]) => setE((x) => ({ ...x, [k]: v }))
  const pickable = images.filter((i) => !e.references.includes(i.rel)).slice(0, 60)
  const full = e.references.length >= 8
  const pending = () => pendingElement(element, e, palette)
  return (
    <div className="mt-3 space-y-3 text-xs" data-plan-form="element">
      <ElementPhoto element={e} base={base} busy={busy} uploading={uploading} describing={describing}
        onUpload={onUploadReference && ((f) => onUploadReference(f, pending()))} onRemove={(r) => set("references", e.references.filter((x) => x !== r))}
        onDescribe={onDescribe && (() => onDescribe(pending()))} />
      <label className="block"><Label>{t("f.kind")}</Label>
        <select value={e.kind} onChange={(ev) => set("kind", ev.target.value as PlanElement["kind"])} className={fieldCls}>
          {ELEMENT_KINDS.map((k) => <option key={k} value={k} data-element-kind={k}>{t(`element_kind.${k}`)}</option>)}
        </select>
      </label>
      <Field name="name" label={t("f.name")} value={e.name} max={200} onChange={(v) => set("name", v)} />
      <Field name="description" label={t("f.description")} value={e.description} max={4000} rows={4} onChange={(v) => set("description", v)} />
      <Field name="style_anchor" label={t("f.style_anchor")} value={e.style_anchor} max={2000} rows={2} onChange={(v) => set("style_anchor", v)} />
      <Field name="palette" label={t("f.palette")} value={palette} max={300} onChange={setPalette} />
      {!full && pickable.length > 0 && (
        <details data-element-refs>
          <summary className="cursor-pointer text-[11px] text-[#8d9ab0] hover:text-[#e8eef8]">{t("f.add_reference")}</summary>
          <div className="mt-1 grid max-h-40 grid-cols-4 gap-1 overflow-y-auto">
            {pickable.map((i) => (
              <button key={i.id} type="button" onClick={() => set("references", [...e.references, i.rel])} data-element-pick={i.rel} title={i.name}
                className="aspect-square overflow-hidden rounded-[3px] bg-[#111827] hover:outline hover:outline-1 hover:outline-[#69d7ff]">
                <img src={fileUrl(i.abs)} alt="" loading="lazy" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </details>
      )}
      <FormActions busy={busy} dirty={dirty} onDelete={onDelete}
        onSave={() => onSave({ kind: e.kind, name: e.name, description: e.description, style_anchor: e.style_anchor,
          palette: paletteFromText(palette), references: e.references })} />
    </div>
  )
}
