import { ArrowLeft, ArrowRight, CheckCircle2, Copy, RefreshCw, Save, Share2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { FlowRail } from "./components/FlowRail"
import { highestAvailableStep } from "./flow"
import type { EntryKind, GameEngine, GameProject, ProjectCreate, ProjectPatch, TargetPlatform } from "./types"

interface Props {
  kind: EntryKind
  project: GameProject | null
  onBack: () => void
  onCreate: (body: ProjectCreate) => Promise<GameProject>
  onUpdate: (project: GameProject, patch: ProjectPatch) => Promise<GameProject>
  onGenerateUnreal: (project: GameProject) => Promise<GameProject>
  onReloadProject: (project: GameProject) => Promise<GameProject>
}

const fieldClass = "w-full rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2.5 text-sm text-[#e8eef8] placeholder:text-[#596579] focus:border-[#69d7ff]/60 focus:outline-none focus:ring-1 focus:ring-[#69d7ff]/40"

export function GuidedFlow({ kind, project, onBack, onCreate, onUpdate, onGenerateUnreal, onReloadProject }: Props) {
  const { t } = useTranslation("gameStudio")
  const [activeStep, setActiveStep] = useState(project?.current_step ?? 1)
  const [engine, setEngine] = useState<GameEngine>(project?.engine ?? "godot")
  const [engineVersion, setEngineVersion] = useState(project?.engine_version ?? "auto")
  const [title, setTitle] = useState(project?.title ?? "")
  const [idea, setIdea] = useState(project?.idea ?? "")
  const [genre, setGenre] = useState(project?.genre ?? "")
  const [platform, setPlatform] = useState<TargetPlatform>(project?.target_platform ?? "desktop")
  const [coreAction, setCoreAction] = useState(project?.core_action ?? "")
  const [successCondition, setSuccessCondition] = useState(project?.success_condition ?? "")
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!project) return
    setActiveStep(project.current_step)
    setEngine(project.engine)
    setEngineVersion(project.engine_version)
    setTitle(project.title)
    setIdea(project.idea)
    setGenre(project.genre)
    setPlatform(project.target_platform)
    setCoreAction(project.core_action)
    setSuccessCondition(project.success_condition)
  }, [project])

  const availableStep = useMemo(() => project ? Math.max(project.current_step, highestAvailableStep(project)) : 1, [project])
  const host = window.location.hostname
  const shareName = project?.sharing.share_name ?? ""
  const sharePath = project?.sharing.enabled ? `//${host}/${shareName}` : ""
  const localMountPath = `$HOME/HydraHive/${shareName}`
  const localProjectPath = project?.engine_project_path ? `${localMountPath}/${project.engine_project_path}` : localMountPath
  const localProjectRoot = localProjectPath.includes("/") ? localProjectPath.slice(0, localProjectPath.lastIndexOf("/")) : localProjectPath
  const buildCommand = `UNREAL_ROOT="/pfad/zu/UnrealEngine" bash "${localProjectRoot}/Scripts/build-editor-linux.sh"`
  const testCommand = `UNREAL_ROOT="/pfad/zu/UnrealEngine" bash "${localProjectRoot}/Scripts/test-linux.sh"`
  const packageCommand = `UNREAL_ROOT="/pfad/zu/UnrealEngine" bash "${localProjectRoot}/Scripts/package-linux.sh"`
  const openCommand = `UNREAL_ROOT="/pfad/zu/UnrealEngine" bash "${localProjectRoot}/Scripts/open-editor-linux.sh"`
  const mountCommand = project?.sharing.enabled
    ? `mkdir -p "${localMountPath}" && sudo mount -t cifs ${sharePath} "${localMountPath}" -o username=${project.sharing.user},uid=$(id -u),gid=$(id -g),file_mode=0775,dir_mode=0775,vers=3.0,noserverino`
    : ""
  const engineVersionValid = engine !== "unreal" || /^(?:auto|\d+\.\d+(?:\.\d+)?)$/.test(engineVersion.trim())
  const canSave = activeStep === 1 ? Boolean(title.trim() && idea.trim() && engineVersionValid)
    : activeStep === 2 ? Boolean(genre.trim())
      : activeStep === 3 ? Boolean(coreAction.trim() && successCondition.trim()) : false

  const copyMountCommand = async () => {
    if (!mountCommand) return
    await navigator.clipboard.writeText(mountCommand)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  const generateUnrealProject = async () => {
    if (!project || project.engine !== "unreal") return
    setGenerating(true)
    setError("")
    try {
      await onGenerateUnreal(project)
    } catch {
      setError(t("flow.generateFailed"))
    } finally {
      setGenerating(false)
    }
  }

  const refreshProject = async () => {
    if (!project) return
    setRefreshing(true)
    setError("")
    try {
      await onReloadProject(project)
    } catch {
      setError(t("flow.refreshFailed"))
    } finally {
      setRefreshing(false)
    }
  }

  const saveAndContinue = async () => {
    if (!canSave) return
    setSaving(true)
    setError("")
    try {
      let current = project
      if (!current) {
        current = await onCreate({ entry_kind: kind, engine, engine_version: engineVersion.trim(), title, idea, genre, target_platform: platform })
      }
      const nextStep = Math.max(current.current_step, Math.min(activeStep + 1, 4))
      const patch: ProjectPatch = {
        revision: current.revision,
        title, idea, genre, target_platform: platform,
        core_action: coreAction,
        success_condition: successCondition,
        current_step: nextStep,
      }
      await onUpdate(current, patch)
      setActiveStep(nextStep)
    } catch {
      setError(t("flow.saveFailed"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
      <button type="button" onClick={onBack} className="mb-4 flex items-center gap-1 text-xs text-[#9aa7bc] hover:text-[#e8eef8]">
        <ArrowLeft size={14} aria-hidden="true" /> {t("flow.back")}
      </button>
      <header className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#69d7ff]">{t(`entry.${kind}.title`)}</p>
        <h1 className="mt-1 text-2xl font-semibold text-[#e8eef8]">{project?.title || t("flow.untitled")}</h1>
        <p className="mt-1 text-sm text-[#9aa7bc]">{t(`flow.intro.${kind}`)}</p>
      </header>

      <FlowRail activeStep={activeStep} availableStep={availableStep} onSelect={setActiveStep} />

      {project && (
        <section className="mt-4 flex flex-col gap-3 rounded-xl border border-emerald-300/20 bg-emerald-300/[0.04] p-4 sm:flex-row sm:items-center" aria-label={t("sharing.title")}>
          <span className="rounded-lg bg-emerald-300/10 p-2 text-emerald-300"><Share2 size={19} aria-hidden="true" /></span>
          <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-[#e8eef8]">{t("sharing.title")}</p><p className="mt-1 break-all font-mono text-[11px] text-emerald-200">{sharePath}</p></div>
          <div className="text-[11px] text-[#9aa7bc]">{t("sharing.user")}: <span className="text-[#c8d2df]">{project.sharing.user}</span></div>
        </section>
      )}

      <section className="mt-5 rounded-2xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-5 sm:p-6">
        <div className="mb-5">
          <span className="text-[11px] font-medium text-[#69d7ff]">{t("flow.stepCount", { step: activeStep })}</span>
          <h2 className="mt-1 text-lg font-semibold text-[#e8eef8]">{t(`flow.panels.${activeStep}.title`)}</h2>
          <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t(`flow.panels.${activeStep}.description`)}</p>
        </div>

        {activeStep === 1 && (
          <div className="space-y-4">
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.engine")}<select value={engine} onChange={(event) => { const selected = event.target.value as GameEngine; setEngine(selected); if (selected !== "unreal") setEngineVersion("auto") }} disabled={Boolean(project)} className={`${fieldClass} mt-1.5 disabled:cursor-not-allowed disabled:opacity-60`}><option value="godot">{t("engine.godot")}</option><option value="unreal">{t("engine.unreal")}</option><option value="unity">{t("engine.unity")}</option></select></label>
            {engine === "unreal" && <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.engineVersion")}<input value={engineVersion} onChange={(event) => setEngineVersion(event.target.value)} disabled={Boolean(project)} maxLength={32} list="unreal-version-options" className={`${fieldClass} mt-1.5 disabled:cursor-not-allowed disabled:opacity-60`} placeholder={t("fields.engineVersionPlaceholder")} /><datalist id="unreal-version-options"><option value="auto" /><option value="5.0" /><option value="5.1" /><option value="5.2" /><option value="5.3" /><option value="5.4" /><option value="5.5" /><option value="5.6" /></datalist>{!engineVersionValid && <span className="mt-1 block text-[11px] text-red-300">{t("fields.engineVersionInvalid")}</span>}</label>}
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.title")}<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={120} className={`${fieldClass} mt-1.5`} placeholder={t("fields.titlePlaceholder")} /></label>
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.idea")}<textarea value={idea} onChange={(event) => setIdea(event.target.value)} maxLength={4000} rows={5} className={`${fieldClass} mt-1.5 resize-y`} placeholder={t(`fields.ideaPlaceholder.${kind}`)} /></label>
          </div>
        )}

        {activeStep === 2 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.genre")}<input value={genre} onChange={(event) => setGenre(event.target.value)} maxLength={120} className={`${fieldClass} mt-1.5`} placeholder={t("fields.genrePlaceholder")} /></label>
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.platform")}<select value={platform} onChange={(event) => setPlatform(event.target.value as TargetPlatform)} className={`${fieldClass} mt-1.5`}><option value="desktop">{t("platform.desktop")}</option><option value="web">{t("platform.web")}</option><option value="mobile">{t("platform.mobile")}</option></select></label>
            <div className="sm:col-span-2 rounded-xl border border-[#69d7ff]/15 bg-[#69d7ff]/[0.04] p-4 text-xs leading-5 text-[#c8d2df]">{idea || t("flow.briefEmpty")}</div>
          </div>
        )}

        {activeStep === 3 && (
          <div className="space-y-4">
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.coreAction")}<textarea value={coreAction} onChange={(event) => setCoreAction(event.target.value)} maxLength={2000} rows={3} className={`${fieldClass} mt-1.5 resize-y`} placeholder={t("fields.coreActionPlaceholder")} /></label>
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.success")}<textarea value={successCondition} onChange={(event) => setSuccessCondition(event.target.value)} maxLength={2000} rows={3} className={`${fieldClass} mt-1.5 resize-y`} placeholder={t("fields.successPlaceholder")} /></label>
          </div>
        )}

        {activeStep === 4 && project && (
          <div className="space-y-4">
            {project.engine === "unreal" && !project.engine_project_ready ? (
              <div className="rounded-xl border border-[#69d7ff]/20 bg-[#69d7ff]/[0.05] p-5">
                <h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.generateUnrealTitle")}</h3>
                <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t("flow.generateUnrealText", { version: project.engine_version })}</p>
                <button type="button" disabled={generating} onClick={() => void generateUnrealProject()} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#69d7ff] px-4 py-2.5 text-sm font-semibold text-[#0d1420] hover:bg-[#9ee6ff] disabled:cursor-not-allowed disabled:opacity-50"><Save size={15} aria-hidden="true" />{generating ? t("flow.generating") : t("flow.generateUnreal")}</button>
              </div>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-emerald-300/20 bg-emerald-300/[0.05] p-4">
                <span className="rounded-lg bg-emerald-300/10 p-2 text-emerald-300"><CheckCircle2 size={20} aria-hidden="true" /></span>
                <div><h3 className="text-sm font-semibold text-[#e8eef8]">{t(project.engine === "unreal" ? "flow.readyTitle" : "flow.workspaceReadyTitle")}</h3><p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t(project.engine === "unreal" ? "flow.readyText" : "flow.workspaceReadyText", { engine: t(`engine.${project.engine}`) })}</p></div>
              </div>
            )}
            {(project.engine !== "unreal" || project.engine_project_ready) && <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-4">
              <h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.linuxMountTitle")}</h3>
              <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t("flow.linuxMountText")}</p>
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#080d16] p-3">
                <code className="min-w-0 flex-1 select-all break-all text-[11px] leading-5 text-emerald-200">{mountCommand}</code>
                <button type="button" onClick={() => void copyMountCommand()} className="shrink-0 rounded-md border border-[rgb(var(--hh-s-rand,42_54_75))] p-2 text-[#9aa7bc] hover:text-[#e8eef8]" aria-label={t("flow.copyCommand")} title={t("flow.copyCommand")}><Copy size={15} aria-hidden="true" /></button>
              </div>
              {copied && <p className="mt-2 text-xs text-emerald-300">{t("flow.copied")}</p>}
              <p className="mt-3 break-all text-xs leading-5 text-[#c8d2df]">{t("flow.openEngine", { engine: t(`engine.${project.engine}`), path: localProjectPath })}</p>
            </div>}
            {project.engine === "unreal" && project.engine_project_ready && <>
              <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-4">
                <h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.localWorkflowTitle")}</h3>
                <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t("flow.localWorkflowText")}</p>
                <button type="button" disabled={generating} onClick={() => void generateUnrealProject()} className="mt-3 flex items-center gap-1 rounded-md border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1.5 text-[11px] text-[#9aa7bc] hover:text-[#e8eef8] disabled:opacity-50"><RefreshCw size={13} className={generating ? "animate-spin" : ""} aria-hidden="true" />{t("flow.syncHelpers")}</button>
                {([["build", buildCommand], ["test", testCommand], ["package", packageCommand], ["open", openCommand]] as const).map(([kind, command]) => <div key={kind} className="mt-3"><p className="mb-1 text-[11px] font-medium text-[#c8d2df]">{t(`flow.localCommand.${kind}`)}</p><code className="block select-all break-all rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#080d16] p-3 text-[11px] leading-5 text-emerald-200">{command}</code></div>)}
              </div>
              <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-4">
                <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.realResultTitle")}</h3><button type="button" disabled={refreshing} onClick={() => void refreshProject()} className="flex items-center gap-1 rounded-md border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1.5 text-[11px] text-[#9aa7bc] hover:text-[#e8eef8] disabled:opacity-50"><RefreshCw size={13} className={refreshing ? "animate-spin" : ""} aria-hidden="true" />{t("flow.refreshResult")}</button></div>
                {project.last_engine_run ? <div className={`mt-3 rounded-lg border p-3 ${project.last_engine_run.status === "passed" ? "border-emerald-300/20 bg-emerald-300/[0.05]" : "border-red-300/20 bg-red-300/[0.05]"}`}><p className={`text-xs font-semibold ${project.last_engine_run.status === "passed" ? "text-emerald-300" : "text-red-300"}`}>{t(`flow.runStatus.${project.last_engine_run.status}`)} · {t(`flow.runKind.${project.last_engine_run.kind}`)}</p><p className="mt-1 text-[11px] text-[#9aa7bc]">{project.last_engine_run.finished_at} · Exit-Code {project.last_engine_run.exit_code}</p><p className="mt-1 break-all font-mono text-[10px] text-[#c8d2df]">{project.last_engine_run.log_path}</p></div> : <p className="mt-3 text-xs leading-5 text-[#9aa7bc]">{t("flow.noRealResult")}</p>}
              </div>
            </>}
          </div>
        )}

        {error && <p role="alert" className="mt-4 text-xs text-red-300">{error}</p>}
        {activeStep <= 3 && (
          <div className="mt-6 flex justify-end">
            <button type="button" disabled={!canSave || saving} onClick={saveAndContinue} className="flex items-center gap-2 rounded-lg bg-[#69d7ff] px-4 py-2.5 text-sm font-semibold text-[#0d1420] transition hover:bg-[#9ee6ff] disabled:cursor-not-allowed disabled:opacity-40">
              {saving ? <Save size={15} aria-hidden="true" /> : <ArrowRight size={15} aria-hidden="true" />}{saving ? t("flow.saving") : t("flow.continue")}
            </button>
          </div>
        )}
      </section>
    </main>
  )
}
