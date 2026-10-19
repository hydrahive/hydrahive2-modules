import { Loader2, Mic } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { jobText } from "./jobLogic"
import type { Job, Shot } from "./planApi"
import { fileOf } from "./planLogic"
import { Label } from "./formParts"
import { Costs } from "./Costs"

/** Sprache des Shots (5c): aus dem Sprechtext erzeugen (Auftrag im Hintergrund), fertige Sprache anhören. */
export function ShotSpeech({ shot, base, job, onGenerate, model }: { shot: Shot; base: string; job: Job | null; onGenerate: () => void
  /** C3: Sprachmodell für den Kosten-Hinweis */
  model?: string }) {
  const { t } = useTranslation("studio")
  const running = job?.status === "running" || job?.status === "queued"
  const error = jobText(t, job)
  const text = (shot.speech ?? "").trim()
  const sound = fileOf(base, shot.voice_rel ?? null)
  return (
    <div className="space-y-2" data-shot-speech>
      <Label>{t("speech")}</Label>
      {sound && <audio src={fileUrl(sound)} controls preload="metadata" className="h-8 w-full" data-shot-speech-player />}
      {!text && <p className="text-[11px] text-[#68758a]">{t("speech_needs_text")}</p>}
      <button type="button" onClick={onGenerate} disabled={running || !text} data-shot-speech-generate
        className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-[#46617f] py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
        {running ? <Loader2 size={13} className="animate-spin" /> : <Mic size={13} />}
        {running ? t("speech_running") : sound ? t("speech_again") : t("speech_generate")}
       <Costs model={model} />
        </button>
      {text && !running && <p className="text-[10px] leading-relaxed text-[#68758a]">{t("speech_cost")}</p>}
      {error && <p className="rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2 py-1.5 text-[11px] leading-relaxed text-[#ff6b8a]" data-shot-speech-error>{error}</p>}
    </div>
  )
}
