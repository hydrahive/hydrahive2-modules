import { useTranslation } from "react-i18next"
import type { TvwBuild, TvwJob } from "./api"
import { buildStep, buildView, lastGood, shortHash, sizeText } from "./buildLogic"
import { errorKey } from "./logic"
import { BOX, BTN_MAIN, MUTED } from "./ui"

const LOG = "max-h-56 overflow-auto whitespace-pre-wrap rounded bg-[rgb(var(--hh-s-innen,36_48_71))] p-2 text-xs " +
  "text-[#9aa7bc]"

/** Bereich „Startbildschirm“: bauen, Fortschritt, Ergebnis (Version, Größe, Prüfsumme), Protokoll. */
export function BuildPanel({ job, builds, ready, busy, onBuild }: {
  job: TvwJob | null | undefined; builds: TvwBuild[]; ready: boolean; busy: boolean; onBuild: () => void
}) {
  const { t } = useTranslation("tvwerkstatt")
  const view = buildView(job, builds)
  const good = lastGood(builds)
  const { n, total } = buildStep(job?.step ?? "")

  return (
    <section className={BOX} aria-label={t("build.title")}>
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("build.title")}</h2>
      <p className={MUTED}>{t("build.explain")}</p>

      {view === "running" && (
        <div className="space-y-1" role="status">
          <p className="text-sm text-[#69d7ff]">{t("build.running", { n, total })}</p>
          <p className={MUTED}>{t(`bstep.${job?.step || "container"}`)}</p>
        </div>
      )}

      {view === "failed" && job && (
        <div className="space-y-2" role="alert">
          <p className="text-sm text-red-300">{t(errorKey(job.error_code))}</p>
          <p className={MUTED}>{t("setup.failed_at", { step: t(`bstep.${job.step || "container"}`) })}</p>
          {job.error_detail && <pre className={LOG}>{job.error_detail}</pre>}
        </div>
      )}

      {good && (
        <div className="space-y-1 text-sm text-[#e8eef8]">
          <p className="text-emerald-300">{t("build.done")}</p>
          <p className={MUTED}>
            {[good.version ? t("build.version", { v: good.version }) : "", sizeText(good.size)].filter(Boolean).join(" · ")}
          </p>
          <p className="text-xs text-[#9aa7bc]" title={good.sha256}>{t("build.hash", { h: shortHash(good.sha256) })}</p>
          <p className="text-xs text-[#9aa7bc]" title={good.commit_id}>
            {t("build.source", { c: good.commit_id.slice(0, 7) })}
          </p>
          {good.log_tail && (
            <details>
              <summary className="cursor-pointer text-xs text-[#9aa7bc]">{t("build.log")}</summary>
              <pre className={LOG}>{good.log_tail}</pre>
            </details>
          )}
        </div>
      )}

      {!ready && <p className={MUTED}>{t("build.need_setup")}</p>}
      {ready && view !== "running" && (
        <button type="button" className={BTN_MAIN} disabled={busy} onClick={onBuild}>
          {t(good ? "build.again" : "build.start")}
        </button>
      )}
    </section>
  )
}
