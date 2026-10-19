/** Geführter Weg des Studios (studio/SPEC.md „Bauplan G“). G1: Gerüst + Schritt „Idee“ echt; Schritte 2–5 folgen.
 *  Die Attrappe-Bausteine (StepCast, StepImages, StepClips, StepFilm, mockData) bleiben als Vorlage für G2–G5. */
import { ArrowLeft, ArrowRight, Check, Clapperboard, Construction, Film, ImageIcon, Lightbulb, Users } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { castOpen, doneSteps, missingImages, STEP_IDS, type StepId } from "./guidedLogic"
import { StepHead } from "./ui"
import { StepCastLive } from "./StepCastLive"
import { StepImagesLive } from "./StepImagesLive"
import { useImages } from "./useImages"
import { StepIdeaLive } from "./StepIdeaLive"
import { useCast } from "./useCast"
import { useGuided, type GuidedState } from "./useGuided"

const ICONS: Record<StepId, typeof Lightbulb> = { 1: Lightbulb, 2: Users, 3: ImageIcon, 4: Clapperboard, 5: Film }

function Steps({ g }: { g: GuidedState }) {
  const { t } = useTranslation("studio")
  const done = doneSteps(g.plan)
  const title = g.plan?.screenplay.title
  return (
    <nav aria-label={t("guided.steps")} className="flex w-64 shrink-0 flex-col gap-1 overflow-y-auto border-r border-[#1c2433] bg-[#0b111b] p-4">
      <label className="mb-3 block text-xs text-[#8d9ab0]">
        {t("guided.project")}
        <select value={g.pid} onChange={(e) => g.setPid(e.target.value)} aria-label={t("guided.project")}
          className="mt-1 w-full rounded-[6px] border border-[#2a364b] bg-[#080b11] px-2 py-1.5 text-sm text-[#e8eef8]">
          {(g.projects ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </label>
      <div className="mb-1 text-xs font-black uppercase tracking-[0.2em] text-[#8d9ab0]">{t("guided.mine")}</div>
      <div className="mb-3 line-clamp-2 text-base font-bold leading-snug text-[#f2f6fc]">{title || t("guided.new_film")}</div>
      {STEP_IDS.map((n) => {
        const Icon = ICONS[n]
        const active = g.step === n
        return (
          <button key={n} type="button" onClick={() => g.setStep(n)} aria-current={active ? "step" : undefined}
            className={`flex items-center gap-3 rounded-[10px] px-3 py-3 text-left ${active ? "bg-[#69d7ff]/15 ring-1 ring-[#69d7ff]/60" : "hover:bg-[#1c2940]/60"}`}>
            <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-black ${done[n] ? "bg-[#3ddc97] text-[#04140d]" : active ? "bg-[#69d7ff] text-[#06111c]" : "bg-[#1c2940] text-[#8d9ab0]"}`}>
              {done[n] ? <Check size={18} /> : n}
            </span>
            <span className="min-w-0">
              <span className={`flex items-center gap-1.5 text-base font-bold ${active ? "text-[#f2f6fc]" : "text-[#c3ccdd]"}`}><Icon size={15} /> {t(`guided.step.${n}.title`)}</span>
              <span className="block text-xs text-[#8d9ab0]">{t(`guided.step.${n}.hint`)}</span>
            </span>
          </button>
        )
      })}
      <div className="mt-auto space-y-2 border-t border-[#1c2433] pt-3 text-xs text-[#8d9ab0]">
        <p>{t("guided.costs_text")}</p>
        <p>{t("guided.pro_text")}</p>
        <a href="/studio" className="font-semibold text-[#69d7ff] underline">{t("guided.pro_link")}</a>
      </div>
    </nav>
  )
}

function Soon({ n }: { n: StepId }) {
  const { t } = useTranslation("studio")
  return (
    <div>
      <StepHead n={n} title={t(`guided.step.${n}.title`)} text={t(`guided.step.${n}.hint`)} />
      <div className="flex items-start gap-3 rounded-[12px] border border-[#2a364b] bg-[#0e1420] p-5">
        <Construction size={22} className="mt-0.5 shrink-0 text-[#ffb86b]" />
        <div className="space-y-2">
          <h2 className="text-lg font-bold text-[#f2f6fc]">{t("guided.soon_title")}</h2>
          <p className="text-base text-[#c3ccdd]">{t("guided.soon_text")}</p>
          <a href="/studio" className="inline-block text-sm font-semibold text-[#69d7ff] underline">{t("guided.soon_link")}</a>
        </div>
      </div>
    </div>
  )
}

function Footer({ g }: { g: GuidedState }) {
  const { t } = useTranslation("studio")
  const next = (g.step + 1) as StepId
  const open = castOpen(g.plan?.elements ?? [])
  const noImage = missingImages(g.plan)
  const gap = g.step === 1 && !g.plan?.scenes.length ? t("guided.gap.1") : g.step === 2 && open ? t("guided.gap.2", { count: open })
    : g.step === 3 && noImage ? t("guided.gap.3", { count: noImage }) : ""
  return (
    <footer className="flex items-center gap-4 border-t border-[#1c2433] bg-[#0b111b] px-8 py-4">
      {g.step > 1 ? <button type="button" onClick={() => g.setStep((g.step - 1) as StepId)} className="flex items-center gap-2 text-sm font-semibold text-[#c3ccdd] hover:text-white"><ArrowLeft size={16} /> {t("guided.back")}</button> : <span />}
      <span className="ml-auto text-sm text-[#8d9ab0]">{gap}</span>
      {g.step < 5 && (
        <button type="button" onClick={() => g.setStep(next)} disabled={g.step === 1 && !g.plan?.scenes.length}
          className="flex items-center gap-2 rounded-[10px] bg-[#69d7ff] px-6 py-3 text-base font-black text-[#06111c] hover:bg-[#8fe2ff] disabled:opacity-40">
          {t("guided.next", { title: t(`guided.step.${next}.title`) })} <ArrowRight size={18} />
        </button>
      )}
    </footer>
  )
}

export function GuidedPage() {
  const { t } = useTranslation("studio")
  const g = useGuided(t)
  const c = useCast(g, t, g.step === 2)
  const im = useImages(g, g.step === 3)
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/studio" context={t("title")} />
      <div className="flex min-h-0 flex-1 text-[#e8eef8]" data-guided-root>
        <Steps g={g} />
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
            <div className="mx-auto max-w-6xl">
              {g.projects && g.projects.length === 0
                ? <p className="rounded-[10px] border border-[#2a364b] p-6 text-base text-[#c3ccdd]">{t("guided.no_project")}</p>
                : g.step === 1 ? <StepIdeaLive g={g} /> : g.step === 2 ? <StepCastLive g={g} c={c} />
                  : g.step === 3 ? <StepImagesLive g={g} im={im} /> : <Soon n={g.step} />}
            </div>
          </main>
          <Footer g={g} />
        </div>
      </div>
    </CockpitShell>
  )
}
