import { ArrowLeft, ArrowRight, LockKeyhole, Save, ShieldCheck } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { FlowRail } from "./components/FlowRail"
import { highestAvailableStep } from "./flow"
import type { DraftCreate, DraftPatch, EntryKind, GameDraft, TargetPlatform } from "./types"

interface Props {
  kind: EntryKind
  draft: GameDraft | null
  onBack: () => void
  onCreate: (body: DraftCreate) => Promise<GameDraft>
  onUpdate: (draft: GameDraft, patch: DraftPatch) => Promise<GameDraft>
}

const fieldClass = "w-full rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2.5 text-sm text-[#e8eef8] placeholder:text-[#596579] focus:border-[#69d7ff]/60 focus:outline-none focus:ring-1 focus:ring-[#69d7ff]/40"

export function GuidedFlow({ kind, draft, onBack, onCreate, onUpdate }: Props) {
  const { t } = useTranslation("gameStudio")
  const [activeStep, setActiveStep] = useState(draft?.current_step ?? 1)
  const [title, setTitle] = useState(draft?.title ?? "")
  const [idea, setIdea] = useState(draft?.idea ?? "")
  const [genre, setGenre] = useState(draft?.genre ?? "")
  const [platform, setPlatform] = useState<TargetPlatform>(draft?.target_platform ?? "desktop")
  const [coreAction, setCoreAction] = useState(draft?.core_action ?? "")
  const [successCondition, setSuccessCondition] = useState(draft?.success_condition ?? "")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!draft) return
    setActiveStep(draft.current_step)
    setTitle(draft.title)
    setIdea(draft.idea)
    setGenre(draft.genre)
    setPlatform(draft.target_platform)
    setCoreAction(draft.core_action)
    setSuccessCondition(draft.success_condition)
  }, [draft])

  const availableStep = useMemo(() => draft ? Math.max(draft.current_step, highestAvailableStep(draft)) : 1, [draft])
  const canSave = activeStep === 1 ? Boolean(title.trim() && idea.trim())
    : activeStep === 2 ? Boolean(genre.trim())
      : activeStep === 3 ? Boolean(coreAction.trim() && successCondition.trim()) : false

  const saveAndContinue = async () => {
    if (!canSave) return
    setSaving(true)
    setError("")
    try {
      let current = draft
      if (!current) {
        current = await onCreate({ entry_kind: kind, title, idea, genre, target_platform: platform })
      }
      const nextStep = Math.max(current.current_step, Math.min(activeStep + 1, 4))
      const patch: DraftPatch = {
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
        <h1 className="mt-1 text-2xl font-semibold text-[#e8eef8]">{draft?.title || t("flow.untitled")}</h1>
        <p className="mt-1 text-sm text-[#9aa7bc]">{t(`flow.intro.${kind}`)}</p>
      </header>

      <FlowRail activeStep={activeStep} availableStep={availableStep} onSelect={setActiveStep} />

      <section className="mt-5 rounded-2xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-5 sm:p-6">
        <div className="mb-5">
          <span className="text-[11px] font-medium text-[#69d7ff]">{t("flow.stepCount", { step: activeStep })}</span>
          <h2 className="mt-1 text-lg font-semibold text-[#e8eef8]">{t(`flow.panels.${activeStep}.title`)}</h2>
          <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t(`flow.panels.${activeStep}.description`)}</p>
        </div>

        {activeStep === 1 && (
          <div className="space-y-4">
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
            <div className="flex items-start gap-3"><span className="rounded-lg bg-amber-300/10 p-2 text-amber-300"><LockKeyhole size={20} aria-hidden="true" /></span><div><h3 className="text-sm font-semibold text-[#e8eef8]">{t("flow.runnerLockedTitle")}</h3><p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t("flow.runnerLockedText")}</p><div className="mt-3 flex items-center gap-2 text-[11px] text-[#c8d2df]"><ShieldCheck size={14} className="text-[#69d7ff]" aria-hidden="true" />{t("flow.runnerSafety")}</div></div></div>
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
