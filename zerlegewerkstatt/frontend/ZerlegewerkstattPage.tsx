// Hauptseite der Zerlege-Werkstatt.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  getCase,
  getReport,
  listCases,
  type CaseFile,
  type Report,
} from "./api"
import { ArtifactPanel } from "./ArtifactPanel"
import { CaseList } from "./CaseList"
import { NewCaseForm } from "./NewCaseForm"
import { ReportPanel } from "./ReportPanel"
import { MUTED, TEXT, input, panel } from "./ui"

export function ZerlegewerkstattPage() {
  const { t } = useTranslation("zerlegewerkstatt")
  const [projectId, setProjectId] = useState("")
  const [cases, setCases] = useState<CaseFile[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [current, setCurrent] = useState<CaseFile | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)

  const loadCases = useCallback((id: string) => {
    if (!id) {
      setCases([])
      return
    }
    setLoading(true)
    listCases(id)
      .then(setCases)
      .catch(() => setCases([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadCases(projectId)
  }, [projectId, loadCases])

  const refresh = useCallback(() => {
    if (!selected) return
    getCase(selected)
      .then((value) => {
        setCurrent(value)
        setReportLoading(true)
        return getReport(selected)
      })
      .then((value) => setReport(value))
      .catch(() => setReport(null))
      .finally(() => setReportLoading(false))
  }, [selected])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Laeuft eine Analyse, wird der Fortschritt regelmaessig geholt.
  useEffect(() => {
    const running = current?.jobs.some(
      (job) => job.status === "queued" || job.status === "running",
    )
    if (!running) return
    const timer = window.setInterval(refresh, 3000)
    return () => window.clearInterval(timer)
  }, [current, refresh])

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header className="space-y-1">
        <h1 className={`text-lg font-semibold ${TEXT}`}>{t("title")}</h1>
        <p className={`text-sm ${MUTED}`}>{t("intro")}</p>
      </header>

      <div className={`${panel}`}>
        <label className={`block text-xs ${MUTED} mb-1`} htmlFor="zw-project">
          {t("project")}
        </label>
        <input
          id="zw-project"
          className={`${input} w-full`}
          value={projectId}
          onChange={(e) => setProjectId(e.target.value.trim())}
          placeholder={t("projectPlaceholder")}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        <div className="space-y-4">
          <CaseList
            cases={cases}
            selected={selected}
            onSelect={setSelected}
            loading={loading}
          />
          {projectId && (
            <NewCaseForm
              projectId={projectId}
              onCreated={(id) => {
                setSelected(id)
                loadCases(projectId)
              }}
            />
          )}
        </div>

        <div className="space-y-4">
          {current ? (
            <>
              <ArtifactPanel caseFile={current} onChanged={refresh} />
              <ReportPanel report={report} jobs={current.jobs} loading={reportLoading} />
            </>
          ) : (
            <div className={`${panel}`}>
              <p className={`text-sm ${MUTED}`}>{t("selectCase")}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
