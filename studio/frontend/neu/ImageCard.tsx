/** G3: Karte einer Szene im Schritt „Bilder“ – Bild im Filmformat, blättern, anderes Bild, wegwerfen, „Mit dabei“. */
import { useState } from "react"
import { ChevronLeft, ChevronRight, ImageIcon, Loader2, PenLine, RefreshCw, Sparkles, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { Costs } from "../Costs"
import { jobText, latestJob } from "../jobLogic"
import type { Job, PlanElement } from "../planApi"
import { fileOf } from "../planLogic"
import { faceOf, shotBusy, type ImageCardData } from "./guidedLogic"
import { SmallButton } from "./ui"

interface Props {
  card: ImageCardData
  base: string
  format: string
  elements: PlanElement[]
  jobs: Job[]
  busy: boolean
  model: string
  onMake: () => void
  onFlip: (dir: -1 | 1) => void
  onDrop: () => void
  onCast: (id: string) => void
  /** H6: gezeigtes Bild gezielt ändern */
  onChange: (text: string) => void
}

export function Face({ el, base, size = 20 }: { el: PlanElement; base: string; size?: number }) {
  const pic = faceOf(el)
  return pic
    ? <img src={fileUrl(fileOf(base, pic))} alt="" style={{ width: size, height: size }} className="rounded-full object-cover" />
    : <span style={{ width: size, height: size }} className="grid place-items-center rounded-full bg-[rgb(var(--hh-s-hebung,42_54_75))] text-[10px] font-black text-[#e8eef8]">{el.name.slice(0, 1).toUpperCase()}</span>
}

export function ImageCard({ card, base, format, elements, jobs, busy, model, onMake, onFlip, onDrop, onCast, onChange }: Props) {
  const { t } = useTranslation("studio")
  const [change, setChange] = useState("")
  const s = card.shot
  const running = shotBusy(jobs, s.id)
  const last = latestJob(jobs, s.id, "image")
  const failed = !running && last?.status === "failed" && !s.image_rel
  const ratio = format === "9:16" ? "aspect-[9/16] max-h-[420px]" : "aspect-video"
  const pos = s.variants.indexOf(s.image_rel ?? "")
  const cast = s.cast ?? []
  return (
    <article className="flex flex-col gap-2 rounded-[12px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,14_20_32))] p-3" data-guided-image={s.id}>
      <div className="flex items-start gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#1c2940] text-xs font-black text-[#69d7ff]">{card.n}</span>
        <p className="text-sm leading-snug text-[#e8eef8]">
          {card.part > 0 && <span className="mr-1 font-bold text-[#9aa7bc]">{t("guided.part", { n: card.part })} ·</span>}{card.text}
        </p>
      </div>
      <div className={`relative mx-auto w-full overflow-hidden rounded-[8px] bg-[rgb(var(--hh-s-grund,8_11_17))] ${ratio}`}>
        {s.image_rel
          ? <img src={fileUrl(fileOf(base, s.image_rel))} alt={card.text} className="h-full w-full object-cover" />
          : <div className="grid h-full place-items-center text-center text-sm text-[#9aa7bc]"><span><ImageIcon className="mx-auto mb-1" size={26} />{t("guided.no_image")}</span></div>}
        {running && <div className="absolute inset-0 grid place-items-center bg-black/60 text-sm text-white"><span className="flex items-center gap-2"><Loader2 className="animate-spin" size={18} /> {t("guided.image_busy")}</span></div>}
        {s.variants.length > 1 && !running && (
          <>
            <button type="button" aria-label={t("guided.prev_image")} onClick={() => onFlip(-1)} disabled={busy} className="absolute left-1 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-1.5 text-white"><ChevronLeft size={18} /></button>
            <button type="button" aria-label={t("guided.next_image")} onClick={() => onFlip(1)} disabled={busy} className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-1.5 text-white"><ChevronRight size={18} /></button>
            <span className="absolute bottom-1 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs text-white">{t("guided.image_n", { n: pos + 1, count: s.variants.length })}</span>
          </>
        )}
      </div>
      {elements.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-[#9aa7bc]">{t("guided.with")}</span>
          {elements.map((e) => {
            const on = cast.includes(e.id)
            return (
              <button key={e.id} type="button" onClick={() => onCast(e.id)} aria-pressed={on} disabled={busy}
                className={`flex items-center gap-1 rounded-full py-0.5 pl-0.5 pr-2 text-xs font-semibold ${on ? "bg-[#3ddc97]/15 text-[#c9f7e2]" : "text-[#5f6d84] line-through"}`}>
                <Face el={e} base={base} /> {e.name}
              </button>
            )
          })}
        </div>
      )}
      {s.image_rel && (
        <div className="space-y-1.5 rounded-[8px] bg-[rgb(var(--hh-s-grund,8_11_17))] p-2">
          <textarea value={change} onChange={(e) => setChange(e.target.value)} rows={2} maxLength={1000} aria-label={t("guided.change_label")}
            placeholder={t("guided.change_placeholder")}
            className="w-full resize-none rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,14_20_32))] p-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]" />
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" data-guided-change disabled={busy || running || !change.trim()} onClick={() => { onChange(change.trim()); setChange("") }}
              className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-3 py-1.5 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
              <PenLine size={14} /> {t("guided.change_image")}<Costs model={model || undefined} />
            </button>
            <span className="text-xs text-[#9aa7bc]">{t("guided.change_hint")}</span>
          </div>
        </div>
      )}
      {failed && <p className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-2 py-1.5 text-xs text-[#ffd9ad]">{jobText(t, last)}</p>}
      <div className="flex flex-wrap gap-2">
        {!s.image_rel
          ? <button type="button" onClick={onMake} disabled={busy || running}
              className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
              {failed ? <RefreshCw size={16} /> : <Sparkles size={16} />}{t(failed ? "guided.image_retry" : "guided.make_image")}<Costs model={model || undefined} />
            </button>
          : <>
              <SmallButton onClick={onMake} disabled={busy || running}><RefreshCw size={14} /> {t("guided.another_image")}<Costs model={model || undefined} /></SmallButton>
              <SmallButton onClick={onDrop} disabled={busy || running}><Trash2 size={14} /> {t("guided.drop_image")}</SmallButton>
            </>}
      </div>
    </article>
  )
}
