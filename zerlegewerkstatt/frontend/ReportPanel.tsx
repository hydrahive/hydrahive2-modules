// Bericht mit den fuenf Abschnitten aus SPEC §11.
import { useTranslation } from "react-i18next"
import type { Job, Report } from "./api"
import { MUTED, TEXT, panel } from "./ui"

interface Props {
  report: Report | null
  jobs: Job[]
  loading: boolean
}

const TABS = ["observed", "derived", "suspected", "unknown", "next_allowed_step"] as const

export function ReportPanel({ report, jobs, loading }: Props) {
  const { t } = useTranslation("zerlegewerkstatt")

  if (loading) {
    return <div className={`${panel} h-24 animate-pulse`} aria-hidden="true" />
  }
  if (!report) {
    return (
      <div className={`${panel}`}>
        <p className={`text-sm ${MUTED}`}>{t("noReport")}</p>
      </div>
    )
  }

  const running = jobs.filter((job) => job.status === "queued" || job.status === "running")

  return (
    <div className={`${panel} space-y-3`}>
      <h2 className={`text-sm font-semibold ${TEXT}`}>{t("report")}</h2>

      {running.length > 0 && (
        <ul className="space-y-1">
          {running.map((job) => (
            <li key={job.id} className={`text-xs ${MUTED}`}>
              {t(`status.${job.status}`)} · {t(`analysis.${job.analysis_type}`)} · {job.progress}%
            </li>
          ))}
        </ul>
      )}

      {jobs
        .filter((job) => job.status === "failed")
        .map((job) => (
          <p key={job.id} className="text-sm text-rose-400">
            {t("analysisFailed")} {job.error_code ? `(${job.error_code})` : ""}
          </p>
        ))}

      {TABS.map((tab) => {
        const lines = report[tab] ?? []
        return (
          <details key={tab} className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
            <summary className={`cursor-pointer text-sm ${TEXT}`}>{t(`sections.${tab}`)}</summary>
            {lines.length === 0 ? (
              <p className={`mt-2 text-xs ${MUTED}`}>{t("reportEmpty")}</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                {lines.map((line, index) => (
                  <li key={index} className={MUTED}>{line}</li>
                ))}
              </ul>
            )}
          </details>
        )
      })}

      {report.evidence.length > 0 && (
        <details className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
          <summary className={`cursor-pointer text-sm ${TEXT}`}>
            {t("evidenceIndex", { count: report.evidence.length })}
          </summary>
          <ul className="mt-2 space-y-2">
            {report.evidence.map((item) => (
              <li key={item.id} className="rounded-md bg-[rgb(var(--hh-s-innen,17_23_35))] p-2 text-xs">
                <code className={`break-all ${TEXT}`}>{item.id}</code>
                <p className={`mt-1 ${MUTED}`}>
                  {t(`analysis.${item.analysis_type}`)} · {item.operation || t("unknownOperation")} · {item.confidence || t("unknownConfidence")}
                </p>
                {(item.provider || item.provider_version) && (
                  <p className={MUTED}>{[item.provider, item.provider_version].filter(Boolean).join(" · ")}</p>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {report.untrusted_target_content && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300">
          {t("untrustedWarning")}
        </p>
      )}
    </div>
  )
}
