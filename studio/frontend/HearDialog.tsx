import { Ear, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { costText, lengthText, type HearInfo } from "./hearLogic"
import { jobText } from "./jobLogic"
import type { Job } from "./planApi"
import { Backdrop } from "./StudioDialogs"
import { Costs } from "./Costs"

interface Props { info: HearInfo | null; language: string; job: Job | null; busy: boolean; onRun: () => void; onClose: () => void }

/** „Aus dem Ton heraushören“ (Spec „Bauplan 6b“): was gehört wird, Sprache, Länge, Modell, Kosten, Starten. */
export function HearDialog({ info, language, job, busy, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("hear_title")}>
      <div className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-4 py-2.5 text-sm font-black text-[#e8eef8]"><Ear size={15} /> {t("hear_title")}</div>
      {info ? <Body info={info} language={language} job={job} busy={busy} onRun={onRun} onClose={onClose} />
        : <p className="p-4 text-xs text-[#9aa7bc]">{t("loading")}</p>}
    </Backdrop>
  )
}

function Body({ info, language, job, busy, onRun, onClose }: Omit<Props, "info"> & { info: HearInfo }) {
  const { t } = useTranslation("studio")
  const running = job?.status === "running" || job?.status === "queued"
  const block = !info.cloud ? "hear_needs_cloud" : !info.audible || info.seconds <= 0 ? "hear_nothing" : info.seconds > info.max_seconds ? "hear_too_long" : null
  const cost = costText(info.seconds)
  const error = jobText(t, job)
  return (
    <div className="flex flex-col gap-2.5 p-4 text-xs text-[#c3ccdd]" data-hear-dialog>
      <p className="leading-relaxed">{t("hear_intro")}</p>
      <p className="text-[#9aa7bc]">{t("hear_no_music")}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-[#9aa7bc]">{t("sub_language")}</dt><dd>{t(`lang.${language}`)}</dd>
        <dt className="text-[#9aa7bc]">{t("hear_length")}</dt><dd>{lengthText(info.seconds)}</dd>
        <dt className="text-[#9aa7bc]">{t("hear_model")}</dt><dd className="truncate font-mono text-[11px]">{info.model}</dd>
        <dt className="text-[#9aa7bc]">{t("hear_cost")}</dt>
        <dd>{cost.key === "hear_cost_below" ? t("hear_cost_below") : t("hear_cost_about", { cents: cost.cents })}</dd>
      </dl>
      {info.existing > 0 && <p className="text-[#ffb86b]">{t("hear_replaces", { count: info.existing })}</p>}
      {block && <p className="text-[#ff6b8a]" role="alert">{t(block)}</p>}
      {running && <p className="flex items-center gap-1.5 text-[#69d7ff]"><Loader2 size={12} className="animate-spin" /> {t("hear_running")}</p>}
      {error && !running && <p className="text-[#ff6b8a]" role="alert">{error}</p>}
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
        <button type="button" disabled={busy || running || !!block} data-hear-run onClick={onRun}
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-40">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Ear size={12} />} {t("hear_run")}
         <Costs model={info?.model} />
        </button>
      </div>
    </div>
  )
}
