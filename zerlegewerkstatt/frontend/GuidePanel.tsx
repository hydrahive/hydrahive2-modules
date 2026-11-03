import { useTranslation } from "react-i18next"
import { MUTED, TEXT, panel } from "./ui"

type TermEntry = { term: string; text: string; example?: string }
type FileEntry = { name: string; examples: string; use: string; note: string }
type AnalysisEntry = { name: string; when: string; result: string }
type ReportEntry = { name: string; text: string }
type WorkflowEntry = { title: string; goal: string; steps: string[]; result: string }
type TroubleEntry = { problem: string; solution: string }

function list<T>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : []
}

function GuideHeading({ children }: { children: string }) {
  return <h3 className={`text-base font-semibold ${TEXT}`}>{children}</h3>
}

export function GuidePanel() {
  const { t } = useTranslation("zerlegewerkstatt")
  const values = <T,>(key: string) => list<T>(t(`guide.${key}`, { returnObjects: true }) as unknown)
  const quickSteps = values<string>("quickSteps")
  const concepts = values<TermEntry>("concepts")
  const caseFields = values<TermEntry>("caseFields")
  const fileTypes = values<FileEntry>("fileTypes")
  const analyses = values<AnalysisEntry>("analyses")
  const reportParts = values<ReportEntry>("reportParts")
  const workflows = values<WorkflowEntry>("workflows")
  const trouble = values<TroubleEntry>("trouble")
  const limits = values<string>("limits")

  return (
    <section className={`${panel} space-y-4`} aria-labelledby="zw-guide-title">
      <div>
        <h2 id="zw-guide-title" className={`text-lg font-semibold ${TEXT}`}>{t("guide.heading")}</h2>
        <p className={`mt-1 text-sm leading-6 ${MUTED}`}>{t("guide.lead")}</p>
      </div>

      <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_23_35))] p-4">
        <h3 className={`text-sm font-semibold ${TEXT}`}>{t("guide.quickTitle")}</h3>
        <ol className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {quickSteps.map((step, index) => (
            <li key={step} className="flex min-w-0 gap-3 text-sm leading-5">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[rgb(var(--hh-s-hebung,27_37_54))] font-semibold text-[#9be6ff]">
                {index + 1}
              </span>
              <span className={MUTED}>{step}</span>
            </li>
          ))}
        </ol>
      </div>

      <details className="group rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.55)]">
        <summary className={`cursor-pointer list-none px-4 py-3 text-sm font-semibold ${TEXT} hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]`}>
          <span className="mr-2 inline-block transition-transform group-open:rotate-90" aria-hidden="true">▶</span>
          {t("guide.openLabel")}
        </summary>

        <div className="space-y-8 border-t border-[rgb(var(--hh-s-rand,42_54_75))] p-4 sm:p-5">
          <p className={`text-xs ${MUTED}`}>{t("guide.closeHint")}</p>

          <section className="space-y-3">
            <GuideHeading>{t("guide.conceptsTitle")}</GuideHeading>
            <p className={`text-sm leading-6 ${MUTED}`}>{t("guide.conceptsIntro")}</p>
            <dl className="grid gap-3 md:grid-cols-2">
              {concepts.map((entry) => (
                <div key={entry.term} className="min-w-0 rounded-lg bg-[rgb(var(--hh-s-innen,17_23_35))] p-3">
                  <dt className={`text-sm font-semibold ${TEXT}`}>{entry.term}</dt>
                  <dd className={`mt-1 text-sm leading-5 ${MUTED}`}>{entry.text}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.caseTitle")}</GuideHeading>
            <p className={`text-sm leading-6 ${MUTED}`}>{t("guide.caseIntro")}</p>
            <div className="space-y-3">
              {caseFields.map((entry) => (
                <div key={entry.term} className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
                  <p className={`text-sm font-semibold ${TEXT}`}>{entry.term}</p>
                  <p className={`mt-1 text-sm leading-5 ${MUTED}`}>{entry.text}</p>
                  {entry.example && <p className="mt-2 text-xs text-[#9be6ff]">{t("guide.exampleLabel")}: {entry.example}</p>}
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.fileTitle")}</GuideHeading>
            <p className={`text-sm leading-6 ${MUTED}`}>{t("guide.fileIntro")}</p>
            <div className="grid gap-3 lg:grid-cols-2">
              {fileTypes.map((entry) => (
                <article key={entry.name} className="min-w-0 rounded-lg bg-[rgb(var(--hh-s-innen,17_23_35))] p-4">
                  <h4 className={`text-sm font-semibold ${TEXT}`}>{entry.name}</h4>
                  <p className="mt-1 break-words text-xs text-[#9be6ff]">{entry.examples}</p>
                  <p className={`mt-2 text-sm leading-5 ${MUTED}`}>{entry.use}</p>
                  <p className="mt-2 text-xs leading-5 text-amber-300/90">{entry.note}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.analysesTitle")}</GuideHeading>
            <p className={`text-sm leading-6 ${MUTED}`}>{t("guide.analysesIntro")}</p>
            <div className="grid gap-3 lg:grid-cols-2">
              {analyses.map((entry) => (
                <article key={entry.name} className="min-w-0 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
                  <h4 className={`text-sm font-semibold ${TEXT}`}>{entry.name}</h4>
                  <p className={`mt-1 text-xs leading-5 ${MUTED}`}><strong className={TEXT}>{t("guide.whenLabel")}:</strong> {entry.when}</p>
                  <p className={`text-xs leading-5 ${MUTED}`}><strong className={TEXT}>{t("guide.resultLabel")}:</strong> {entry.result}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.reportTitle")}</GuideHeading>
            <p className={`text-sm leading-6 ${MUTED}`}>{t("guide.reportIntro")}</p>
            <dl className="space-y-2">
              {reportParts.map((entry) => (
                <div key={entry.name} className="rounded-lg bg-[rgb(var(--hh-s-innen,17_23_35))] p-3 sm:flex sm:gap-4">
                  <dt className={`shrink-0 text-sm font-semibold sm:w-44 ${TEXT}`}>{entry.name}</dt>
                  <dd className={`mt-1 text-sm leading-5 sm:mt-0 ${MUTED}`}>{entry.text}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.workflowsTitle")}</GuideHeading>
            <div className="grid gap-4 xl:grid-cols-2">
              {workflows.map((workflow) => (
                <article key={workflow.title} className="min-w-0 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-4">
                  <h4 className={`text-sm font-semibold ${TEXT}`}>{workflow.title}</h4>
                  <p className={`mt-1 text-sm leading-5 ${MUTED}`}>{workflow.goal}</p>
                  <ol className={`mt-3 list-decimal space-y-2 pl-5 text-sm leading-5 ${MUTED}`}>
                    {workflow.steps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                  <p className="mt-3 text-xs leading-5 text-[#9be6ff]">{workflow.result}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.troubleTitle")}</GuideHeading>
            <div className="space-y-2">
              {trouble.map((entry) => (
                <details key={entry.problem} className="rounded-lg bg-[rgb(var(--hh-s-innen,17_23_35))] px-3 py-2">
                  <summary className={`cursor-pointer text-sm font-medium ${TEXT}`}>{entry.problem}</summary>
                  <p className={`mt-2 text-sm leading-5 ${MUTED}`}>{entry.solution}</p>
                </details>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <GuideHeading>{t("guide.limitsTitle")}</GuideHeading>
            <ul className={`list-disc space-y-2 pl-5 text-sm leading-5 ${MUTED}`}>
              {limits.map((entry) => <li key={entry}>{entry}</li>)}
            </ul>
          </section>
        </div>
      </details>
    </section>
  )
}
