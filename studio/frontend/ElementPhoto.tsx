import { useRef, useState } from "react"
import { ImagePlus, Loader2, Sparkles, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { PlanElement } from "./planApi"
import { fileOf } from "./planLogic"
import { acceptFor, filesFromDrop, isFileDrag } from "./uploadLogic"

interface Props {
  element: PlanElement
  base: string
  busy: boolean
  uploading: boolean
  describing: boolean
  /** fehlt → kein Hochladen (z. B. ohne Rechte), Fotos werden nur gezeigt */
  onUpload?: (file: File) => void
  onRemove: (rel: string) => void
  onDescribe?: () => void
}

/** Ganz oben im Baustein (C2): Vorlage-Fotos groß, Foto hierher ziehen/auswählen, aus dem Foto beschreiben lassen. */
export function ElementPhoto({ element, base, busy, uploading, describing, onUpload, onRemove, onDescribe }: Props) {
  const { t } = useTranslation("studio")
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const refs = element.references
  const full = refs.length >= 8
  const take = (files: File[]) => { const f = files.find((x) => /\.(png|jpe?g|webp|gif)$/i.test(x.name)); if (f && !full) onUpload?.(f) }
  return (
    <div data-element-photo onDragOver={(e) => { if (onUpload && isFileDrag(e.dataTransfer)) { e.preventDefault(); setOver(true) } }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { if (!isFileDrag(e.dataTransfer)) return; e.preventDefault(); setOver(false); take(filesFromDrop(e.dataTransfer)) }}
      className={`space-y-2 rounded-[6px] border border-dashed p-2 ${over ? "border-[#69d7ff] bg-[#1c2940]" : "border-[#46617f] bg-[#0d1420]"}`}>
      <input ref={input} type="file" accept={acceptFor("reference")} hidden onChange={(e) => { take(Array.from(e.target.files ?? [])); e.target.value = "" }} />
      {refs.length ? (
        <div className="grid grid-cols-2 gap-1.5">
          {refs.map((r) => (
            <span key={r} className="relative aspect-square overflow-hidden rounded-[4px] bg-[#111827]" data-element-ref={r}>
              <img src={fileUrl(fileOf(base, r))} alt="" className="h-full w-full object-cover" />
              <button type="button" onClick={() => onRemove(r)} aria-label={t("photo_remove")} title={t("photo_remove")}
                className="absolute right-1 top-1 rounded bg-black/75 p-0.5 text-[#e8eef8] hover:text-[#ff6b8a]"><X size={12} /></button>
            </span>
          ))}
        </div>
      ) : null}
      {onUpload && <button type="button" onClick={() => input.current?.click()} disabled={busy || uploading || full} data-element-photo-pick
        className={`flex w-full flex-col items-center justify-center gap-1 rounded-[4px] text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-40 ${refs.length ? "py-1.5" : "py-6"}`}>
        {uploading ? <Loader2 size={refs.length ? 14 : 22} className="animate-spin" /> : <ImagePlus size={refs.length ? 14 : 22} />}
        {refs.length ? t(full ? "upload_reference_full" : "photo_more") : t("photo_drop")}
      </button>}
      <p className="text-[10px] leading-relaxed text-[#8d9ab0]">{t("photo_why", { name: element.name || t("untitled") })}</p>
      {refs.length > 0 && onDescribe && (
        <button type="button" onClick={onDescribe} disabled={busy || describing} data-element-describe
          className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-[#46617f] py-1.5 text-[11px] font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
          {describing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} {describing ? t("photo_describing") : t("photo_describe")}
        </button>
      )}
    </div>
  )
}
