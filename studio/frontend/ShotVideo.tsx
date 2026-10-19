import { Film, Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { jobText } from "./jobLogic"
import type { Job, Shot } from "./planApi"
import { fileOf } from "./planLogic"
import { Label } from "./formParts"

interface Props {
  shot: Shot
  base: string
  job: Job | null
  onGenerate: () => void
  /** C1: Video löschen */
  onDelete?: (rel: string) => void
}

/** Video des Shots: aus dem gewählten Bild erzeugen (Auftrag im Hintergrund), fertiges Video abspielen. */
export function ShotVideo({ shot, base, job, onGenerate, onDelete }: Props) {
  const { t } = useTranslation("studio")
  const running = job?.status === "running" || job?.status === "queued" || shot.status === "video_processing"
  const error = jobText(t, job)
  const video = fileOf(base, shot.video_rel)
  return (
    <div className="space-y-2" data-shot-video>
      <Label>{t("video")}</Label>
      {video && (
        <video src={fileUrl(video)} poster={shot.image_rel ? fileUrl(fileOf(base, shot.image_rel)) : undefined} controls preload="metadata"
          className="aspect-video w-full rounded-[3px] bg-black" data-shot-video-player />
      )}
      {video && onDelete && shot.video_rel && !running && (
        <button type="button" onClick={() => onDelete(shot.video_rel as string)} data-shot-video-delete
          className="flex items-center gap-1 text-[11px] text-[#8d9ab0] hover:text-[#ff6b8a]"><Trash2 size={11} /> {t("video_delete")}</button>
      )}
      {!shot.image_rel && <p className="text-[11px] text-[#68758a]">{t("video_needs_image")}</p>}
      <button type="button" onClick={onGenerate} disabled={running || !shot.image_rel} data-shot-video-generate
        className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-[#46617f] py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
        {running ? <Loader2 size={13} className="animate-spin" /> : <Film size={13} />}
        {running ? t("video_running") : video ? t("video_again") : t("video_generate", { seconds: shot.duration })}
      </button>
      {error && <p className="rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2 py-1.5 text-[11px] leading-relaxed text-[#ff6b8a]" data-shot-video-error>{error}</p>}
    </div>
  )
}
