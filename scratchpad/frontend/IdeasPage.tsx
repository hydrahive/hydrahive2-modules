import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { HelpButton } from "@/i18n/HelpButton"
import { IdeaDetail } from "./components/IdeaDetail"
import { IdeaForm } from "./components/IdeaForm"
import { IdeaList } from "./components/IdeaList"
import { BUTTON, ERROR_BOX, PANEL } from "./components/styles"
import { filterIdeas, linkedIdea, projectShowing, statusShowing, toListItem } from "./ideaView"
import { errorText } from "./saveState"
import type { T } from "./texts.de"
import type { ProjectFilter, StatusFilter } from "./types"
import { useIdeas } from "./useIdeas"

/** Seite „Ideen“ unter /scratchpad: oben festhalten, links die Liste, rechts die ausgewählte Idee.
 *  /scratchpad?idea=<id> öffnet eine Idee direkt, zum Beispiel aus dem Task heraus. */
export function IdeasPage() {
  const { t: translate, i18n } = useTranslation("scratchpad")
  const t: T = useCallback((key, vars) => String(translate(key, vars)), [translate])
  const {
    ideas, projects, active, loading, loadFailed, tasksInstalled,
    reload, select, create, update, createTask, remove, removeNote, forget,
  } = useIdeas()
  const [project, setProject] = useState<ProjectFilter>("all")
  const [status, setStatus] = useState<StatusFilter>("open")
  const [selectError, setSelectError] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const errorOf = useCallback((error: unknown) => errorText(error, t), [t])
  const [params, setParams] = useSearchParams()
  const linkParam = params.get("idea")
  const handledLink = useRef<string | null>(null)

  async function onCreate(data: { title: string; body: string; project_id: string | null }) {
    const idea = await create(data)
    // Die neue Idee soll in der Liste zu sehen sein, auch wenn der Filter sie gerade ausblenden würde.
    if (filterIdeas([toListItem(idea)], project, status).length === 0) {
      setProject("all")
      setStatus("open")
    }
  }

  /** Idee öffnen. Bei einem Direktlink gehen die Filter so weit auf, dass sie auch in der Liste steht. */
  const openIdea = useCallback(async (id: string, viaLink = false) => {
    setSelectError(null)
    try {
      const idea = await select(id)
      if (viaLink && idea) {
        const row = toListItem(idea)
        setProject((current) => projectShowing(row, current))
        setStatus((current) => statusShowing(row, current))
      }
      if (window.matchMedia("(max-width: 1023px)").matches) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    } catch (problem) {
      setSelectError(errorOf(problem))
      if ((problem as { status?: number }).status === 404) forget(id)
    }
  }, [select, forget, errorOf])

  useEffect(() => {
    if (linkParam === null) {
      handledLink.current = null
      return
    }
    // Läuft der Effekt für denselben Verweis zweimal, zählt nur der erste Lauf.
    if (handledLink.current === linkParam) return
    handledLink.current = linkParam
    const id = linkedIdea(linkParam)
    queueMicrotask(() => {
      // Den Verweis nur einmal auswerten: danach gilt wieder, was in der Liste gewählt wird.
      setParams((current) => { const next = new URLSearchParams(current); next.delete("idea"); return next }, { replace: true })
      if (id) void openIdea(id, true)
    })
  }, [linkParam, openIdea, setParams])

  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[rgb(var(--hh-s-grund,8_11_17))]" hideHeader>
      <CockpitTopbar active="/scratchpad" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto max-w-6xl space-y-5">
          <header className="flex flex-wrap items-end gap-3">
            <div className="min-w-0">
              <h1 className="text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1>
              <p className="mt-0.5 text-sm text-[#9aa7bc]">{t("subtitle")}</p>
            </div>
            <div className="ml-auto"><HelpButton topic="scratchpad" /></div>
          </header>

          <IdeaForm projects={projects} t={t} onCreate={onCreate} errorOf={errorOf} />

          {loadFailed && (
            <div role="alert" className={`${ERROR_BOX} flex flex-wrap items-center gap-3`}>
              <span>{t("load_error")}</span>
              <button type="button" onClick={() => void reload()} className={BUTTON}>{t("retry")}</button>
            </div>
          )}
          {selectError && <p role="alert" className={ERROR_BOX}>{selectError}</p>}

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
            <IdeaList ideas={ideas} projects={projects} project={project} status={status} activeId={active?.id ?? null}
              loading={loading} locale={i18n.language} t={t} onProject={setProject} onStatus={setStatus}
              onSelect={(id) => void openIdea(id)} />
            <div ref={detailRef} className="min-w-0 scroll-mt-4">
              {active ? (
                <IdeaDetail key={active.id} idea={active} projects={projects} locale={i18n.language} t={t}
                  onUpdate={update} onRemove={remove} onRemoveNote={removeNote} tasksInstalled={tasksInstalled}
                  onCreateTask={createTask} onGone={forget} errorOf={errorOf} />
              ) : (
                <p className={`${PANEL} hidden px-4 py-10 text-center text-sm text-[#9aa7bc] lg:block`}>{t("detail_empty")}</p>
              )}
            </div>
          </div>
        </div>
      </main>
    </CockpitShell>
  )
}
