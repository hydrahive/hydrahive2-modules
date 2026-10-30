/** G2: Karte einer Figur / eines Ortes – Foto geben → Probebild → „Passt“; oder „Kein Foto“. */
import { useState } from "react"
import { Check, ImagePlus, Loader2, MapPin, Package, RefreshCw, Trash2, User, Wand2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { Costs } from "../Costs"
import { jobText } from "../jobLogic"
import type { Job, PlanElement } from "../planApi"
import { fileOf } from "../planLogic"
import { acceptFor, filesFromDrop, isFileDrag } from "../uploadLogic"
import { castState } from "./guidedLogic"
import { SmallButton } from "./ui"

interface Props {
  el: PlanElement
  base: string
  jobs: Job[]
  uploading: boolean
  busy: boolean
  imageModel: string
  onName: (v: string) => void
  onDescription: (v: string) => void
  onPhoto: (f: File) => void
  onProbe: () => void
  onApprove: () => void
  onReopen: () => void
  onNoPhoto: (v: boolean) => void
  onOtherPhoto: () => void
  onDelete: () => void
  /** H1: Aussehen aus dem Foto neu beschreiben (nur Aussehen, ohne Situation) */
  onRedescribe: () => void
}

const ICON = { character: User, place: MapPin, object: Package }
const btn = "inline-flex items-center gap-2 rounded-[8px] px-4 py-2.5 text-sm font-bold disabled:opacity-50"
const main = `${btn} bg-[#3ddc97] text-[#04140d] hover:bg-[#5ee6aa]`
const plain = `${btn} border border-[rgb(var(--hh-s-rand-hover,70_97_127))] text-[#e8eef8] hover:bg-[#1c2940]`

function Field({ value, label, rows, placeholder, onSave }: { value: string; label: string; rows?: number; placeholder?: string; onSave: (v: string) => void }) {
  const [v, setV] = useState(value)
  const cls = "w-full rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-grund,8_11_17))] px-2 py-1.5 text-[#f2f6fc] outline-none focus:border-[#69d7ff]"
  const blur = () => { if (v.trim() && v !== value) onSave(v.trim()) }
  return rows
    ? <textarea value={v} onChange={(e) => setV(e.target.value)} onBlur={blur} rows={rows} aria-label={label} placeholder={placeholder} maxLength={4000} className={`${cls} text-sm`} />
    : <input value={v} onChange={(e) => setV(e.target.value)} onBlur={blur} aria-label={label} maxLength={200} className={`${cls} min-w-0 flex-1 text-base font-bold`} />
}

export function PersonCard(p: Props) {
  const { t } = useTranslation("studio")
  const [over, setOver] = useState(false)
  const state = p.uploading ? "busy" : castState(p.el, p.jobs)
  const Icon = ICON[p.el.kind]
  const what = t(p.el.kind === "place" ? "guided.the_place" : p.el.kind === "object" ? "guided.the_object" : "guided.the_character")
  const photo = p.el.references[0]
  const job = p.jobs.filter((j) => j.kind === "probe" && j.target === p.el.id).sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null
  const pick = (files: File[]) => { if (files[0]) p.onPhoto(files[0]) }
  return (
    <article data-guided-person={p.el.id} className={`flex flex-col gap-3 rounded-[12px] border p-4 ${state === "approved" ? "border-[#3ddc97]/60 bg-[#3ddc97]/5" : "border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,14_20_32))]"}`}>
      <div className="flex items-center gap-2">
        <Icon size={18} className="shrink-0 text-[#69d7ff]" />
        <Field key={`n:${p.el.name}`} value={p.el.name} label={t("guided.name")} onSave={p.onName} />
        <SmallButton label={t("guided.delete_entry", { name: p.el.name })} onClick={p.onDelete} disabled={p.busy}><Trash2 size={14} /></SmallButton>
      </div>

      {(state === "empty" || state === "photo") && (
        <div className="grid gap-2">
          <label onDragOver={(e) => { if (isFileDrag(e.dataTransfer)) { e.preventDefault(); setOver(true) } }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); pick(filesFromDrop(e.dataTransfer)) }}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-[10px] border-2 border-dashed p-6 text-center text-sm text-[#c3ccdd] hover:border-[#69d7ff] ${over ? "border-[#69d7ff] bg-[#69d7ff]/10" : "border-[rgb(var(--hh-s-rand-hover,70_97_127))]"}`}>
            <input type="file" accept={acceptFor("reference")} className="sr-only" onChange={(e) => { pick(Array.from(e.target.files ?? [])); e.target.value = "" }} />
            {photo ? <img src={fileUrl(fileOf(p.base, photo))} alt={t("guided.your_photo")} className="h-24 rounded-[6px] object-cover" /> : <ImagePlus size={28} className="text-[#69d7ff]" />}
            <span className="font-bold">{t("guided.photo_drop")}</span>
            <span className="text-xs text-[#9aa7bc]">{t("guided.photo_hint")}</span>
          </label>
          {photo && <button type="button" className={main} onClick={p.onProbe} disabled={p.busy}><Wand2 size={16} /> {t("guided.probe_show")}<Costs model={p.imageModel || undefined} /></button>}
          <button type="button" className={plain} onClick={() => p.onNoPhoto(true)} disabled={p.busy}><Wand2 size={16} /> {t("guided.no_photo", { what })}</button>
        </div>
      )}

      {photo && state !== "busy" && (
        <div className="space-y-1 rounded-[10px] bg-[rgb(var(--hh-s-grund,8_11_17))] p-3" data-guided-looks>
          <Field key={`l:${p.el.description}`} value={p.el.description} label={t("guided.looks", { name: p.el.name })} rows={2}
            placeholder={t("guided.description_placeholder")} onSave={p.onDescription} />
          <p className="text-xs text-[#9aa7bc]">{t("guided.looks_hint")}</p>
          <SmallButton onClick={p.onRedescribe} disabled={p.busy}>{t("guided.redescribe")}<Costs model={undefined} /></SmallButton>
        </div>
      )}

      {state === "busy" && (
        <div className="flex items-center gap-3 rounded-[10px] bg-[rgb(var(--hh-s-grund,8_11_17))] p-6 text-sm text-[#c3ccdd]">
          <Loader2 size={20} className="animate-spin text-[#69d7ff]" /> {t(p.uploading ? "guided.uploading" : "guided.probe_busy")}
        </div>
      )}

      {state === "failed" && (
        <div className="space-y-2 rounded-[10px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 p-3 text-sm text-[#ffd9ad]">
          <p>{jobText(t, job)}</p>
          <button type="button" className={plain} onClick={p.onProbe} disabled={p.busy}><RefreshCw size={16} /> {t("guided.probe_retry")}<Costs model={p.imageModel || undefined} /></button>
        </div>
      )}

      {(state === "probe" || state === "approved") && p.el.probe_rel && (
        <div className="space-y-2">
          <div className={`grid gap-2 ${photo ? "grid-cols-[1fr_2fr]" : "grid-cols-1"}`}>
            {photo && <figure><img src={fileUrl(fileOf(p.base, photo))} alt={t("guided.your_photo")} className="aspect-square w-full rounded-[8px] object-cover" />
              <figcaption className="mt-1 text-center text-xs text-[#9aa7bc]">{t("guided.your_photo")}</figcaption></figure>}
            <figure><img src={fileUrl(fileOf(p.base, p.el.probe_rel))} alt={t("guided.probe_caption", { name: p.el.name })} className="aspect-video w-full rounded-[8px] object-cover" />
              <figcaption className="mt-1 text-center text-xs text-[#9aa7bc]">{t("guided.probe_caption", { name: p.el.name })}</figcaption></figure>
          </div>
          {state === "probe" ? (
            <div className="flex flex-wrap gap-2">
              <button type="button" className={main} onClick={p.onApprove} disabled={p.busy}><Check size={16} /> {t("guided.approve")}</button>
              <button type="button" className={plain} onClick={p.onProbe} disabled={p.busy}><RefreshCw size={16} /> {t("guided.probe_again")}<Costs model={p.imageModel || undefined} /></button>
              <button type="button" className={plain} onClick={p.onOtherPhoto} disabled={p.busy}>{t("guided.other_photo")}</button>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-2 text-sm font-bold text-[#3ddc97]">
              <span className="flex items-center gap-1"><Check size={16} /> {t("guided.approved_text", { name: p.el.name })}</span>
              <SmallButton onClick={p.onReopen} disabled={p.busy}>{t("guided.change")}</SmallButton>
            </div>
          )}
        </div>
      )}

      {state === "no_photo" && (
        <div className="space-y-2 rounded-[10px] bg-[rgb(var(--hh-s-grund,8_11_17))] p-3 text-sm text-[#c3ccdd]">
          <p>{t("guided.invents", { what })}</p>
          <Field key={`d:${p.el.description}`} value={p.el.description} label={t("guided.description")} rows={2} placeholder={t("guided.description_placeholder")} onSave={p.onDescription} />
          <div className="flex flex-wrap gap-2">
            <button type="button" className={plain} onClick={p.onProbe} disabled={p.busy || !p.el.description}><Wand2 size={16} /> {t("guided.probe_show")}<Costs model={p.imageModel || undefined} /></button>
            <SmallButton onClick={() => p.onNoPhoto(false)} disabled={p.busy}>{t("guided.photo_after_all")}</SmallButton>
          </div>
        </div>
      )}
    </article>
  )
}
