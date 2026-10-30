import { ImagePlus, Loader2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { jobText } from "./jobLogic"
import type { Job, Shot } from "./planApi"
import { fileOf } from "./planLogic"
import { Label } from "./formParts"
import { Costs } from "./Costs"

interface Props {
  shot: Shot
  base: string
  job: Job | null
  onGenerate: () => void
  /** C3: Modell aus dem Drehbuch für den Kosten-Hinweis (leer = Standard des Servers) */
  model?: string
  onChoose: (rel: string) => void
  /** C1: Variante löschen (Rückfrage übernimmt der Aufrufer) */
  onDelete?: (rel: string) => void
}

/** Bild des Shots: erzeugen (Auftrag im Hintergrund), Varianten ansehen und eine wählen. */
export function ShotImage({ shot, base, job, onGenerate, model, onChoose, onDelete }: Props) {
  const { t } = useTranslation("studio")
  const running = job?.status === "running" || job?.status === "queued"
  const error = jobText(t, job)
  // Shots von vor 3a haben keine Varianten-Liste: das vorhandene Bild ist dann die einzige Wahl
  const variants = shot.variants ?? (shot.image_rel ? [shot.image_rel] : [])
  return (
    <div className="space-y-2" data-shot-image>
      <Label>{t("image")}</Label>
      {variants.length > 0 ? (
        <div className="grid grid-cols-4 gap-1">
          {variants.map((v) => (
            <span key={v} className="relative">
              <button type="button" onClick={() => onChoose(v)} data-shot-variant={v} aria-pressed={v === shot.image_rel}
                title={t("image_choose")}
                className={`block aspect-video w-full overflow-hidden rounded-[3px] border ${v === shot.image_rel ? "border-[#69d7ff]" : "border-transparent hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))]"}`}>
                <img src={fileUrl(fileOf(base, v))} alt="" loading="lazy" className="h-full w-full object-cover" />
              </button>
              {onDelete && (
                <button type="button" onClick={() => onDelete(v)} data-shot-variant-delete={v} aria-label={t("image_delete")} title={t("image_delete")}
                  className="absolute right-0.5 top-0.5 rounded bg-black/75 p-0.5 text-[#e8eef8] hover:text-[#ff6b8a]"><X size={11} /></button>
              )}
            </span>
          ))}
        </div>
      ) : <p className="text-[11px] text-[#9aa7bc]">{t("image_none")}</p>}
      <button type="button" onClick={onGenerate} disabled={running} data-shot-generate
        className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
        {running ? <Loader2 size={13} className="animate-spin" /> : <ImagePlus size={13} />}
        {running ? t("image_running") : variants.length ? t("image_again") : t("image_generate")}
       <Costs model={model} />
        </button>
      {error && <p className="rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2 py-1.5 text-[11px] leading-relaxed text-[#ff6b8a]" data-shot-error>{error}</p>}
    </div>
  )
}
