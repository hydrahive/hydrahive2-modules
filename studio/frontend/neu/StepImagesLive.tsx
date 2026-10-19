/** G3 Schritt 3 „Bilder“: Sammelknopf mit Fortschritt, Karten je Szene, Wegwerfen mit eigener Rückfrage. */
import { Loader2, Sparkles, Square } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Costs } from "../Costs"
import { DeleteDialog } from "../DeleteDialog"
import type { Job } from "../planApi"
import { imageCards } from "./guidedLogic"
import { ImageCard } from "./ImageCard"
import { StepHead } from "./ui"
import type { GuidedState } from "./useGuided"
import type { ImageActions } from "./useImages"

export function ImagesHead({ open, total, batch, model, busy, onAll, onStop }: {
  open: number; total: number; batch: Job | null; model: string; busy: boolean; onAll: () => void; onStop: () => void
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
  if (!open) return null
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <button type="button" onClick={onAll} disabled={busy} data-guided-all-images
        className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2.5 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
        <Sparkles size={16} /> {open === total ? t("guided.all_images") : t("guided.missing_images", { count: open })}<Costs model={model || undefined} />
      </button>
      <span className="text-sm text-[#8d9ab0]">{t("guided.images_hint")}</span>
    </div>
  )
}

export function StepImagesLive({ g, im }: { g: GuidedState; im: ImageActions }) {
  const { t } = useTranslation("studio")
  const cards = imageCards(g.plan)
  const model = g.plan?.screenplay.models.image ?? ""
  if (!cards.length) {
    return (
      <div>
        <StepHead n={3} title={t("guided.step.3.title")} text={t("guided.images_head")} />
        <div className="space-y-3 rounded-[10px] border border-[#2a364b] p-6 text-base text-[#c3ccdd]">
          <p>{t("guided.no_scenes")}</p>
          <button type="button" onClick={() => g.setStep(1)} className="rounded-[8px] border border-[#46617f] px-4 py-2 text-sm font-bold text-[#e8eef8] hover:bg-[#1c2940]">{t("guided.to_idea")}</button>
        </div>
      </div>
    )
  }
  return (
    <div>
      <StepHead n={3} title={t("guided.step.3.title")} text={t("guided.images_head")} />
      <ImagesHead open={cards.filter((c) => !c.shot.image_rel).length} total={cards.length} batch={im.batch} model={model} busy={g.busy}
        onAll={() => void im.all()} onStop={() => void im.stop()} />
      {g.error && <p className="mb-3 rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{g.error}</p>}
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {cards.map((c) => (
          <ImageCard key={c.shot.id} card={c} base={g.plan?.base ?? ""} format={g.plan?.screenplay.aspect_ratio ?? "16:9"}
            elements={g.plan?.elements ?? []} jobs={im.jobs} busy={g.busy} model={model}
            onMake={() => void im.make(c)} onFlip={(d) => im.flip(c, d)} onDrop={() => im.setDropping(c)} onCast={(id) => im.cast(c, id)}
            onChange={(text) => void im.change(c, text)} />
        ))}
      </div>
      {im.dropping && <DeleteDialog name={t("guided.drop_question", { n: im.dropping.n })} busy={g.busy} onConfirm={im.confirmDrop} onClose={() => im.setDropping(null)} />}
    </div>
  )
}
