import type { Ref } from "react"
import { useTranslation } from "react-i18next"
import { errorKey } from "./logic"
import { SUBMIT_STEPS, submitProgress, titleOk, type Target } from "./githubLogic"
import { BTN, BTN_MAIN, INPUT } from "./ui"

interface Props {
  titleId: string; target: Target; title: string; body: string; running: boolean; progress: string; error: string
  detail: unknown; result: { number: number; url: string } | null
  onTarget: (t: Target) => void; onTitle: (t: string) => void; onBody: (t: string) => void; onSubmit: () => void
  onClose: () => void; dialogRef?: Ref<HTMLDivElement>
}

function details(detail: unknown): string[] {
  if (Array.isArray(detail)) return detail.map(String)
  if (detail && typeof detail === "object" && Array.isArray((detail as { failures?: unknown }).failures))
    return (detail as { failures: unknown[] }).failures.map(String)
  return []
}

/** „Änderung einreichen“: Ziel, Titel, Text → Prüfen und einreichen mit Schritten; Ergebnis als Link zum PR. */
export function SubmitDialogView({ titleId, target, title, body, running, progress, error, detail, result, onTarget, onTitle, onBody, onSubmit, onClose, dialogRef }: Props) {
  const { t } = useTranslation("hydralabor")
  const step = submitProgress(progress)
  const lines = details(detail)
  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
      <div className="w-full max-w-lg space-y-3 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] p-5">
        <h2 id={titleId} className="text-base font-semibold text-[#e8eef8]">{t("submit.title")}</h2>
        <p className="text-sm text-[#c8d2df]">{t("submit.intro")}</p>
        <fieldset className="space-y-1 text-sm text-[#c8d2df]" disabled={running}>
          <legend>{t("submit.target")}</legend>
          {(["core", "modules"] as Target[]).map((k) => (
            <label key={k} className="mr-4 inline-flex items-center gap-2">
              <input type="radio" name="target" checked={target === k} onChange={() => onTarget(k)} />{t(`submit.target_${k}`)}
            </label>
          ))}
        </fieldset>
        <label className="block space-y-1 text-sm text-[#c8d2df]"><span>{t("submit.name")}</span>
          <input className={INPUT} value={title} maxLength={120} disabled={running} onChange={(e) => onTitle(e.target.value)} /></label>
        <label className="block space-y-1 text-sm text-[#c8d2df]"><span>{t("submit.body")}</span>
          <textarea className={INPUT} rows={3} value={body} maxLength={4000} disabled={running} onChange={(e) => onBody(e.target.value)} /></label>
        {running && (
          <ol className="space-y-0.5 text-sm" aria-live="polite">
            {SUBMIT_STEPS.map((k, i) => (
              <li key={k} className={i < step ? "text-emerald-300" : i === step ? "text-[#e8eef8]" : "text-[#9aa7bc]"}>
                <span aria-hidden="true">{i < step ? "✓ " : i === step ? "… " : "· "}</span>{t(`submit.step.${k}`)}</li>
            ))}
          </ol>
        )}
        {error && !running && (
          <div role="alert" className="rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
            {t(errorKey(error))}
            {lines.length > 0 && <ul className="mt-1 list-disc pl-5 break-all">{lines.slice(0, 20).map((l) => <li key={l}>{l}</li>)}</ul>}
          </div>
        )}
        {result && !running && (
          <p className="text-sm text-emerald-300">{t("submit.done")}{" "}
            <a className="underline" href={result.url} target="_blank" rel="noreferrer">#{result.number}</a></p>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" className={BTN} disabled={running} onClick={onClose}>{t("submit.close")}</button>
          {!running && !result && (
            <button type="button" className={BTN_MAIN} disabled={!titleOk(title)} onClick={onSubmit}>{t("submit.send")}</button>
          )}
        </div>
      </div>
    </div>
  )
}
