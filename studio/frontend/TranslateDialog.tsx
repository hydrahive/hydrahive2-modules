import { Languages, Loader2 } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { fieldCls, Label } from "./formParts"
import { jobText } from "./jobLogic"
import type { Job } from "./planApi"
import { Backdrop } from "./StudioDialogs"
import { targetChoices, type LanguageList } from "./translateLogic"
import { Costs } from "./Costs"

interface Props {
  list: LanguageList | null
  from: string
  count: number
  model: string
  job: Job | null
  busy: boolean
  onRun: (to: string, replace: boolean) => void
  onClose: () => void
}

/** „Übersetzen“ (Spec 6c): Zielsprache wählen; die Zeiten bleiben, nur die Texte werden übersetzt. */
export function TranslateDialog({ list, from, count, model, job, busy, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  const targets = targetChoices(list, from)
  const [to, setTo] = useState(targets.find((x) => x.count > 0)?.language ?? targets[0]?.language ?? "")
  const existing = targets.find((x) => x.language === to)?.count ?? 0
  const running = job?.status === "running" || job?.status === "queued"
  const error = jobText(t, job)
  return (
    <Backdrop onClose={onClose} label={t("translate_title")}>
      <div className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-4 py-2.5 text-sm font-black text-[#e8eef8]"><Languages size={15} /> {t("translate_title")}</div>
      <div className="flex flex-col gap-2.5 p-4 text-xs text-[#c3ccdd]" data-translate-dialog>
        <p>{t("translate_from", { name: t(`lang.${from}`), count })}</p>
        <label className="block"><Label>{t("translate_to")}</Label>
          <select value={to} onChange={(e) => setTo(e.target.value)} className={fieldCls} data-translate-to>
            {targets.map((x) => <option key={x.language} value={x.language}>{t(`lang.${x.language}`)}{x.count ? ` (${x.count})` : ""}</option>)}
          </select>
        </label>
        <p className="text-[#9aa7bc]">{t("translate_times")}</p>
        <p className="text-[#9aa7bc]">{t("translate_model", { model: model || t("translate_model_default") })} · {t("translate_cost")}</p>
        {existing > 0 && <p className="text-[#ffb86b]">{t("translate_replaces", { count: existing })}</p>}
        {running && <p className="flex items-center gap-1.5 text-[#69d7ff]"><Loader2 size={12} className="animate-spin" /> {t("translate_running")}</p>}
        {error && !running && <p className="text-[#ff6b8a]" role="alert">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" disabled={busy || running || !to || !count} data-translate-run onClick={() => onRun(to, existing > 0)}
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-40">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Languages size={12} />} {t("translate_run")}
           <Costs model={model} />
        </button>
        </div>
      </div>
    </Backdrop>
  )
}
