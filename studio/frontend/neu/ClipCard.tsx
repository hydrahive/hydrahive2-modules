/** G4: Karte einer Szene im Schritt „Bewegung“ – Clip stumm in Schleife oder Standbild, bewegen/wegwerfen. */
import { Clapperboard, Loader2, Pause, RefreshCw, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { Costs } from "../Costs"
import { jobText, latestJob } from "../jobLogic"
import type { Job } from "../planApi"
import { fileOf } from "../planLogic"
import { motionState, shotBusy, type ImageCardData } from "./guidedLogic"
import { SmallButton } from "./ui"

interface Props {
  card: ImageCardData
  base: string
  format: string
  jobs: Job[]
  busy: boolean
  model: string
  onMove: () => void
  onStill: (v: boolean) => void
  onDrop: () => void
}

const main = "inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50"

export function ClipCard({ card, base, format, jobs, busy, model, onMove, onStill, onDrop }: Props) {
  const { t } = useTranslation("studio")
  const s = card.shot
  const state = motionState(s)
  const running = shotBusy(jobs, s.id, "video")
  const last = latestJob(jobs, s.id, "video")
  const failed = !running && last?.status === "failed" && state !== "moving"
  const ratio = format === "9:16" ? "aspect-[9/16] max-h-[420px]" : "aspect-video"
  const off = busy || running
  return (
    <article className="flex flex-col gap-2 rounded-[12px] border border-[#2a364b] bg-[#0e1420] p-3" data-guided-clip={s.id} data-motion={state}>
      <div className="flex items-start gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#1c2940] text-xs font-black text-[#69d7ff]">{card.n}</span>
        <p className="text-sm leading-snug text-[#e8eef8]">
          {card.part > 0 && <span className="mr-1 font-bold text-[#8d9ab0]">{t("guided.part", { n: card.part })} ·</span>}{card.text}
        </p>
      </div>
      <div className={`relative mx-auto w-full overflow-hidden rounded-[8px] bg-[#080b11] ${ratio}`}>
        {state === "moving" && s.video_rel
          ? <video src={fileUrl(fileOf(base, s.video_rel))} muted loop autoPlay playsInline className="h-full w-full object-cover" />
          : s.image_rel
            ? <img src={fileUrl(fileOf(base, s.image_rel))} alt={card.text} className="h-full w-full object-cover" />
            : <div className="grid h-full place-items-center p-4 text-center text-sm text-[#8d9ab0]">{t("guided.need_image")}</div>}
        {running && <div className="absolute inset-0 grid place-items-center bg-black/60 text-sm text-white"><span className="flex items-center gap-2"><Loader2 className="animate-spin" size={18} /> {t("guided.motion_busy")}</span></div>}
        {state === "moving" && <span className="absolute left-2 top-2 rounded-full bg-[#3ddc97] px-2 py-0.5 text-xs font-bold text-[#04140d]">{t("guided.moving_badge")}</span>}
        {state === "still" && <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-bold text-white">{t("guided.still_badge", { n: s.duration })}</span>}
      </div>
      {failed && <p className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-2 py-1.5 text-xs text-[#ffd9ad]">{jobText(t, last)}</p>}
      {state !== "no_image" && (
        <div className="flex flex-wrap gap-2">
          {state === "open" && <>
            <button type="button" className={main} onClick={onMove} disabled={off}><Clapperboard size={16} /> {t("guided.move")}<Costs model={model || undefined} /></button>
            <SmallButton onClick={() => onStill(true)} disabled={off}><Pause size={14} /> {t("guided.keep_still")}</SmallButton>
          </>}
          {state === "still" && <SmallButton onClick={onMove} disabled={off}><Clapperboard size={14} /> {t("guided.move_anyway")}<Costs model={model || undefined} /></SmallButton>}
          {state === "moving" && <>
            <SmallButton onClick={onMove} disabled={off}><RefreshCw size={14} /> {t("guided.move_again")}<Costs model={model || undefined} /></SmallButton>
            <SmallButton onClick={onDrop} disabled={off}><Trash2 size={14} /> {t("guided.drop_motion")}</SmallButton>
          </>}
        </div>
      )}
    </article>
  )
}
