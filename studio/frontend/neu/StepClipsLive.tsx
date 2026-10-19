/** G4 Schritt 4 „Bewegung“: Sammelknopf mit Fortschritt, Karten je Szene, Bewegung wegwerfen mit eigener Rückfrage. */
import { Clapperboard, Loader2, Square } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Costs } from "../Costs"
import { DeleteDialog } from "../DeleteDialog"
import type { Job } from "../planApi"
import { imageCards, motionState } from "./guidedLogic"
import { ClipCard } from "./ClipCard"
import { StepHead } from "./ui"
import type { GuidedState } from "./useGuided"
import type { ClipActions } from "./useClips"

export function ClipsHead({ left, total, batch, model, busy, onAll, onStop }: {
  left: number; total: number; batch: Job | null; model: string; busy: boolean; onAll: () => void; onStop: () => void
}) {
  const { t } = useTranslation("studio")
  if (batch?.progress) {
    return (
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-[10px] border border-[#69d7ff]/40 bg-[#69d7ff]/5 p-3 text-sm text-[#cdeeff]">
        <Loader2 size={16} className="animate-spin" /> {t("guided.batch_progress", { done: batch.progress.done, total: batch.progress.total })}
        <button type="button" onClick={onStop} className="ml-auto inline-flex items-center gap-1 rounded-[6px] border border-[#46617f] px-3 py-1.5 text-xs font-bold text-[#e8eef8] hover:bg-[#1c2940]">
          <Square size={12} /> {t("guided.stop")}
        </button>
      </div>
    )
  }
  if (!left) return null
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <button type="button" onClick={onAll} disabled={busy} data-guided-all-motion
        className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2.5 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
        <Clapperboard size={16} /> {left === total ? t("guided.all_motion") : t("guided.rest_motion", { count: left })}<Costs model={model || undefined} />
      </button>
      <span className="text-sm text-[#8d9ab0]">{t("guided.motion_hint")}</span>
    </div>
  )
}

export function StepClipsLive({ g, cl }: { g: GuidedState; cl: ClipActions }) {
  const { t } = useTranslation("studio")
  const cards = imageCards(g.plan)
  const model = g.plan?.screenplay.models.video ?? ""
  const withImage = cards.filter((c) => motionState(c.shot) !== "no_image")
  return (
    <div>
      <StepHead n={4} title={t("guided.step.4.title")} text={t("guided.clips_head")} />
      {!cards.length ? (
        <div className="space-y-3 rounded-[10px] border border-[#2a364b] p-6 text-base text-[#c3ccdd]">
          <p>{t("guided.no_scenes")}</p>
          <button type="button" onClick={() => g.setStep(1)} className="rounded-[8px] border border-[#46617f] px-4 py-2 text-sm font-bold text-[#e8eef8] hover:bg-[#1c2940]">{t("guided.to_idea")}</button>
        </div>
      ) : (
        <>
          <ClipsHead left={withImage.filter((c) => motionState(c.shot) === "open").length} total={withImage.length} batch={cl.batch} model={model}
            busy={g.busy} onAll={() => void cl.all()} onStop={() => void cl.stop()} />
          {g.error && <p className="mb-3 rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{g.error}</p>}
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {cards.map((c) => (
              <ClipCard key={c.shot.id} card={c} base={g.plan?.base ?? ""} format={g.plan?.screenplay.aspect_ratio ?? "16:9"} jobs={cl.jobs}
                busy={g.busy} model={model} onMove={() => void cl.move(c)} onStill={(v) => cl.still(c, v)} onDrop={() => cl.setDropping(c)} />
            ))}
          </div>
        </>
      )}
      {cl.dropping && <DeleteDialog name={t("guided.drop_motion_question", { n: cl.dropping.n })} busy={g.busy} onConfirm={cl.confirmDrop} onClose={() => cl.setDropping(null)} />}
    </div>
  )
}
