import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { ContainerState, TvwJob } from "./api"
import { setupView, stepIndex } from "./setupLogic"
import { errorKey } from "./logic"
import { BOX, BTN, BTN_DANGER, BTN_MAIN, MUTED } from "./ui"

export interface SetupActions {
  onSetup: (acceptLicense: boolean) => void
  onStop: () => void
  onRemove: () => void
}

/** Bereich „Bauumgebung“: einrichten (mit Lizenz-Bestätigung), Fortschritt, Fehler mit Ausgabe, anhalten, abbauen. */
export function SetupPanel({ job, container, busy, actions }: {
  job: TvwJob | null; container: ContainerState; busy: boolean; actions: SetupActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [license, setLicense] = useState(false)
  const view = setupView(job, container)
  const { n, total } = stepIndex(job?.step ?? "")

  return (
    <section className={BOX} aria-label={t("setup.title")}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-[#e8eef8]">{t("setup.title")}</h2>
        <span className="text-xs text-[#9aa7bc]">{t(`container.${container}`)}</span>
      </div>
      <p className={MUTED}>{t("setup.explain")}</p>

      {view === "running" && (
        <div className="space-y-1" role="status">
          <p className="text-sm text-[#69d7ff]">{t("setup.running", { n, total })}</p>
          <p className={MUTED}>{t(`step.${job?.step || "network"}`)}</p>
        </div>
      )}

      {view === "failed" && job && (
        <div className="space-y-2" role="alert">
          <p className="text-sm text-red-300">{t(errorKey(job.error_code))}</p>
          <p className={MUTED}>{t("setup.failed_at", { step: t(`step.${job.step || "network"}`) })}</p>
          {job.error_detail && (
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-[rgb(var(--hh-s-innen,36_48_71))] p-2
              text-xs text-[#9aa7bc]">{job.error_detail}</pre>
          )}
        </div>
      )}

      {view === "ready" && <p className="text-sm text-emerald-300">{t("setup.ready")}</p>}

      {view !== "running" && view !== "ready" && (
        <div className="space-y-2">
          <label className="flex items-start gap-2 text-sm text-[#e8eef8]">
            <input type="checkbox" checked={license} onChange={(e) => setLicense(e.target.checked)} className="mt-1" />
            <span>{t("setup.license")}</span>
          </label>
          <button type="button" className={BTN_MAIN} disabled={!license || busy}
            onClick={() => actions.onSetup(license)}>
            {t(view === "failed" ? "setup.retry" : "setup.start")}
          </button>
        </div>
      )}

      {view !== "running" && container !== "missing" && (
        <div className="flex flex-wrap gap-2">
          {container === "running" && (
            <button type="button" className={BTN} disabled={busy} onClick={actions.onStop}>{t("setup.stop")}</button>
          )}
          <button type="button" className={BTN_DANGER} disabled={busy} onClick={actions.onRemove}>
            {t("setup.remove")}
          </button>
        </div>
      )}
    </section>
  )
}
