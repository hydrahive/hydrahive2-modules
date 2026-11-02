// Hauptseite der Zerlege-Werkstatt.
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
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
import { ProjectPicker, type SelectableProject } from "./ProjectPicker"
import { ReportPanel } from "./ReportPanel"
import { MUTED, TEXT, panel } from "./ui"

export function ZerlegewerkstattPage() {
  const { t } = useTranslation("zerlegewerkstatt")
  const [projectId, setProjectId] = useState("")
  const [projects, setProjects] = useState<SelectableProject[]>([])
  const [projectsStatus, setProjectsStatus] = useState<"loading" | "ready" | "error">("loading")
  const [cases, setCases] = useState<CaseFile[]>([])
  const [casesError, setCasesError] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [current, setCurrent] = useState<CaseFile | null>(null)
  const [caseError, setCaseError] = useState(false)
  const [report, setReport] = useState<Report | null>(null)
  const [reportError, setReportError] = useState(false)
  const [loading, setLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const projectRef = useRef("")
  const casesRequestRef = useRef(0)
  const selectedRef = useRef<string | null>(null)

  const chooseProject = useCallback((id: string) => {
    projectRef.current = id
    casesRequestRef.current += 1
    selectedRef.current = null
    setProjectId(id)
    setSelected(null)
    setCurrent(null)
    setReport(null)
    setCaseError(false)
    setReportError(false)
    setCases([])
    setCasesError(false)
    setLoading(false)
    setReportLoading(false)
  }, [])

  useEffect(() => {
    let active = true
    projectsApi.list().then((items) => {
      if (!active) return
      setProjects(items)
      setProjectsStatus("ready")
      if (items.length > 0) chooseProject(items[0].id)
    }).catch(() => {
      if (active) setProjectsStatus("error")
    })
    return () => { active = false }
  }, [chooseProject])

  const loadCases = useCallback((id: string) => {
    if (!id) return
    const request = ++casesRequestRef.current
    const isCurrent = () => projectRef.current === id && casesRequestRef.current === request
    setLoading(true)
    setCasesError(false)
    listCases(id)
      .then((items) => { if (isCurrent()) setCases(items) })
      .catch(() => { if (isCurrent()) setCasesError(true) })
      .finally(() => { if (isCurrent()) setLoading(false) })
  }, [])

  useEffect(() => {
    loadCases(projectId)
  }, [projectId, loadCases])

  const chooseCase = useCallback((id: string) => {
    selectedRef.current = id
    setSelected(id)
    setCurrent(null)
    setReport(null)
    setCaseError(false)
    setReportError(false)
  }, [])

  const refresh = useCallback(() => {
    if (!selected) return
    setReportLoading(true)
    getCase(selected)
      .then((value) => {
        if (selectedRef.current !== selected) return
        setCurrent(value)
        setCaseError(false)
        return getReport(selected).then((result) => {
          if (selectedRef.current === selected) {
            setReport(result)
            setReportError(false)
          }
        }).catch(() => {
          if (selectedRef.current === selected) setReportError(true)
        })
      })
      .catch(() => {
        if (selectedRef.current === selected) setCaseError(true)
      })
      .finally(() => {
        if (selectedRef.current === selected) setReportLoading(false)
      })
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

      <ProjectPicker projects={projects} projectId={projectId} status={projectsStatus} onChange={chooseProject} />

      {projectId && <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        <div className="space-y-4">
          {casesError ? (
            <div className={panel} role="alert">
              <p className="text-sm text-rose-400">{t("casesError")}</p>
              <button className={`mt-2 text-sm ${TEXT} underline`} onClick={() => loadCases(projectId)}>{t("retry")}</button>
            </div>
          ) : (
            <CaseList cases={cases} selected={selected} onSelect={chooseCase} loading={loading} />
          )}
          <NewCaseForm
            projectId={projectId}
            onCreated={(id) => {
              chooseCase(id)
              loadCases(projectId)
            }}
          />
        </div>

        <div className="space-y-4">
          {caseError ? (
            <div className={panel} role="alert">
              <p className="text-sm text-rose-400">{t("caseError")}</p>
              <button className={`mt-2 text-sm ${TEXT} underline`} onClick={refresh}>{t("retry")}</button>
            </div>
          ) : current ? (
            <>
              <ArtifactPanel caseFile={current} onChanged={refresh} />
              {reportError ? (
                <div className={panel} role="alert">
                  <p className="text-sm text-rose-400">{t("reportError")}</p>
                  <button className={`mt-2 text-sm ${TEXT} underline`} onClick={refresh}>{t("retry")}</button>
                </div>
              ) : <ReportPanel report={report} jobs={current.jobs} loading={reportLoading} />}
            </>
          ) : (
            <div className={panel}>
              <p className={`text-sm ${MUTED}`}>{selected ? t("caseLoading") : t("selectCase")}</p>
            </div>
          )}
        </div>
      </div>}
    </div>
  )
}
