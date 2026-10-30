import { Loader2, Square } from "lucide-react"
import { useTranslation } from "react-i18next"
import { presetLabel } from "./deliverLogic"
import { jobText } from "./jobLogic"
import type { Job } from "./planApi"
import { cancellable } from "./queueLogic"

interface Props {
  /** Film-Aufträge (queueJobs), älteste oben */
  jobs: Job[]
  /** ID des Auftrags, der gerade abgebrochen wird */
  cancelling: string | null
  onCancel: (id: string) => void
}

const COLORS: Record<string, string> = { queued: "text-[#9aa7bc]", running: "text-[#ffb86b]", done: "text-[#7ee2a8]", failed: "text-[#ff6b8a]", cancelled: "text-[#9aa7bc]" }

/** Warteschlange der Ausgabe (7c): jeder Film mit Vorlage und Zustand, Abbrechen bei wartend/laufend. */
export function RenderQueue({ jobs, cancelling, onCancel }: Props) {
  const { t } = useTranslation("studio")
  if (!jobs.length) return null
  return (
    <div className="space-y-1.5" data-render-queue>
      <h3 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("queue_title")}</h3>
      <ul className="space-y-1">
        {jobs.map((j) => {
          const info = j.info ?? {}
          const status = j.status === "failed" ? jobText(t, j) : j.status === "running"
            ? t("queue_status.running", { percent: j.progress?.done ?? 0 }) : t(`queue_status.${j.status}`)
          return (
            <li key={j.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5" data-queue-item={j.status}>
              <span className="text-[#e8eef8]">{presetLabel(t, info) || t("queue_film")}</span>
              {info.subtitles && <span className="text-[#9aa7bc]">{t("queue_subtitles")}</span>}
              <span className={`flex items-center gap-1 ${COLORS[j.status] ?? ""}`}>
                {j.status === "running" && <Loader2 size={11} className="animate-spin" />}{status}
              </span>
              {cancellable(j) && (
                <button type="button" onClick={() => onCancel(j.id)} disabled={cancelling === j.id} data-queue-cancel
                  className="ml-auto flex items-center gap-1 rounded px-1.5 py-0.5 text-[#9aa7bc] hover:text-[#ff6b8a] disabled:opacity-50">
                  <Square size={10} /> {cancelling === j.id ? t("queue_cancelling") : t("queue_cancel")}
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
