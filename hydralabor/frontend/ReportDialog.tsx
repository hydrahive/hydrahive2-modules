import type { Ref } from "react"
import { useTranslation } from "react-i18next"
import { errorKey } from "./logic"
import { titleOk, type Target } from "./githubLogic"
import { BTN, BTN_MAIN, INPUT } from "./ui"

interface Props {
  titleId: string; target: Target; title: string; what: string; expected: string; steps: string; busy: boolean
  error: string; result: { number: number; url: string } | null; onChange: (k: string, v: string) => void
  onSubmit: () => void; onClose: () => void; dialogRef?: Ref<HTMLDivElement>
}

/** „Fehler melden“: Formular → Meldung bei GitHub. Nur Versionen + Betriebssystem werden angehängt. */
export function ReportDialogView({ titleId, target, title, what, expected, steps, busy, error, result, onChange, onSubmit, onClose, dialogRef }: Props) {
  const { t } = useTranslation("hydralabor")
  const field = (k: "what" | "expected" | "steps", rows: number) => (
    <label className="block space-y-1 text-sm text-[#c8d2df]"><span>{t(`report.${k}`)}</span>
      <textarea className={INPUT} rows={rows} value={{ what, expected, steps }[k]} maxLength={4000} disabled={busy} onChange={(e) => onChange(k, e.target.value)} /></label>
  )
  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
      <div className="w-full max-w-lg space-y-3 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] p-5">
        <h2 id={titleId} className="text-base font-semibold text-[#e8eef8]">{t("report.title")}</h2>
        <fieldset className="space-y-1 text-sm text-[#c8d2df]" disabled={busy}>
          <legend>{t("submit.target")}</legend>
          {(["core", "modules"] as Target[]).map((k) => (
            <label key={k} className="mr-4 inline-flex items-center gap-2">
              <input type="radio" name="rtarget" checked={target === k} onChange={() => onChange("target", k)} />{t(`submit.target_${k}`)}
            </label>
          ))}
        </fieldset>
        <label className="block space-y-1 text-sm text-[#c8d2df]"><span>{t("report.name")}</span>
          <input className={INPUT} value={title} maxLength={120} disabled={busy} onChange={(e) => onChange("title", e.target.value)} /></label>
        {field("what", 3)}{field("expected", 2)}{field("steps", 3)}
        <p className="text-xs text-[#9aa7bc]">{t("report.privacy")}</p>
        {error && <p role="alert" className="text-sm text-red-300">{t(errorKey(error))}</p>}
        {result && <p className="text-sm text-emerald-300">{t("report.done")}{" "}
          <a className="underline" href={result.url} target="_blank" rel="noreferrer">#{result.number}</a></p>}
        <div className="flex justify-end gap-2">
          <button type="button" className={BTN} onClick={onClose}>{t("report.close")}</button>
          {!result && <button type="button" className={BTN_MAIN} disabled={busy || !titleOk(title) || !what.trim()}
            onClick={onSubmit}>{t("report.send")}</button>}
        </div>
      </div>
    </div>
  )
}
