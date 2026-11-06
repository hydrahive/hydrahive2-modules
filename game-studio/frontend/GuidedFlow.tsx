import { ArrowLeft, ArrowRight, LockKeyhole, Save, Share2, ShieldCheck } from "lucide-react"
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
}

const fieldClass = "w-full rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2.5 text-sm text-[#e8eef8] placeholder:text-[#596579] focus:border-[#69d7ff]/60 focus:outline-none focus:ring-1 focus:ring-[#69d7ff]/40"

export function GuidedFlow({ kind, project, onBack, onCreate, onUpdate }: Props) {
  const { t } = useTranslation("gameStudio")
  const [activeStep, setActiveStep] = useState(project?.current_step ?? 1)
  const [engine, setEngine] = useState<GameEngine>(project?.engine ?? "godot")
  const [title, setTitle] = useState(project?.title ?? "")
  const [idea, setIdea] = useState(project?.idea ?? "")
  const [genre, setGenre] = useState(project?.genre ?? "")
  const [platform, setPlatform] = useState<TargetPlatform>(project?.target_platform ?? "desktop")
  const [coreAction, setCoreAction] = useState(project?.core_action ?? "")
  const [successCondition, setSuccessCondition] = useState(project?.success_condition ?? "")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!project) return
    setActiveStep(project.current_step)
    setEngine(project.engine)
    setTitle(project.title)
    setIdea(project.idea)
    setGenre(project.genre)
    setPlatform(project.target_platform)
    setCoreAction(project.core_action)
    setSuccessCondition(project.success_condition)
  }, [project])

  const availableStep = useMemo(() => project ? Math.max(project.current_step, highestAvailableStep(project)) : 1, [project])
  const sharePath = project?.sharing.enabled
    ? project.sharing.platform === "mac"
      ? `smb://${window.location.hostname}/${project.sharing.share_name}`
      : `\\\\${window.location.hostname}\\${project.sharing.share_name}`
    : ""
  const canSave = activeStep === 1 ? Boolean(title.trim() && idea.trim())
    : activeStep === 2 ? Boolean(genre.trim())
      : activeStep === 3 ? Boolean(coreAction.trim() && successCondition.trim()) : false

  const saveAndContinue = async () => {
    if (!canSave) return
    setSaving(true)
    setError("")
    try {
      let current = project
      if (!current) {
        current = await onCreate({ entry_kind: kind, engine, title, idea, genre, target_platform: platform })
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
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.engine")}<select value={engine} onChange={(event) => setEngine(event.target.value as GameEngine)} disabled={Boolean(project)} className={`${fieldClass} mt-1.5 disabled:cursor-not-allowed disabled:opacity-60`}><option value="godot">{t("engine.godot")}</option><option value="unreal">{t("engine.unreal")}</option><option value="unity">{t("engine.unity")}</option></select></label>
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
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.coreAction")}<textarea value={coreAction} onChange={(event) => setCoreAction(event.target.value)} maxLength={2000} rows={3} className={`${fieldClass} mt-1.5 resize-y`} /></label>
            <label className="block text-xs font-medium text-[#c8d2df]">{t("fields.success")}<textarea value={successCondition} onChange={(event) => setSuccessCondition(event.target.value)} maxLength={2000} rows={3} className={`${fieldClass} mt-1.5 resize-y`} /></label>
          </div>
        )}

        {activeStep >= 4 && (
          <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.05] p-5">
            <div className="flex items-start gap-3"><span className="rounded-lg bg-amber-300/10 p-2 text-amber-300"><LockKeyhole size={20} aria-hidden="true" /></span><div><h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.runnerLockedTitle")}</h3><p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{project?.engine === "godot" ? t("flow.runnerLockedGodot") : t("flow.runnerLockedExternal", { engine: project ? t(`engine.${project.engine}`) : "" })}</p><div className="mt-3 flex items-center gap-2 text-[11px] text-[#c8d2df]"><ShieldCheck size={14} className="text-[#69d7ff]" aria-hidden="true" />{t("flow.runnerSafety")}</div></div></div>
            <button type="button" disabled className="mt-5 w-full cursor-not-allowed rounded-lg bg-[#69d7ff]/20 px-4 py-2.5 text-sm font-medium text-[#9aa7bc] opacity-60">{t("flow.buildDisabled")}</button>
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
