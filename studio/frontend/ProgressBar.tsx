import { ArrowRight } from "lucide-react"
import { useTranslation } from "react-i18next"
import { nextStep, type Overview } from "./guideLogic"
import type { Workspace } from "./workspaces"

/** Kopfzeile: wie weit der Film ist und der nächste Schritt als Knopf (erst, wenn es Shots gibt). */
export function ProgressBar({ overview: o, onGo }: { overview: Overview | null; onGo: (w: Workspace) => void }) {
  const { t } = useTranslation("studio")
  if (!o || !o.shots) return null
  const next = nextStep(o)
  const done = (a: number) => (a >= o.shots ? "text-[#5fd38d]" : "text-[#c3ccdd]")
  return (
    <div className="flex shrink-0 items-center gap-2 text-[11px]" data-studio-progress>
      <span className="text-[#9aa7bc]">{t("progress_shots", { count: o.shots })}</span>
      <span className={done(o.with_image)}>{t("progress_images", { done: o.with_image, total: o.shots })}</span>
      <span className={done(o.with_video)}>{t("progress_videos", { done: o.with_video, total: o.shots })}</span>
      <span className={o.clips ? "text-[#5fd38d]" : "text-[#9aa7bc]"}>{o.clips ? t("progress_cut_done") : t("progress_cut_open")}</span>
      {next && (
        <button type="button" onClick={() => onGo(next.workspace)} data-studio-next={next.step}
          className="flex items-center gap-1 rounded-[4px] bg-[#1c2940] px-2 py-0.5 font-bold text-[#69d7ff] hover:bg-[rgb(var(--hh-s-hebung,36_52_79))]">
          {t(`next.${next.step}`)} <ArrowRight size={11} />
        </button>
      )}
    </div>
  )
}
