import { ImagePlus, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { LibraryItem } from "./api"
import { fieldCls, Label } from "./formParts"
import { freeValid, MAX_FREE_COUNT, MAX_FREE_PROMPT, MAX_FREE_REFS, toggleRef, type FreeFormState } from "./freeLogic"
import { jobText } from "./jobLogic"
import type { Catalog } from "./modelCatalog"
import { ModelPick } from "./ModelPick"
import { ASPECTS, type Job } from "./planApi"
import { Costs } from "./Costs"

interface Props {
  form: FreeFormState
  catalog: Catalog | null
  /** Bilder der Bibliothek als mögliche Referenzen */
  images: LibraryItem[]
  job: Job | null
  busy: boolean
  onChange: (f: FreeFormState) => void
  onRun: () => void
}

const COUNTS = Array.from({ length: MAX_FREE_COUNT }, (_, i) => i + 1)

/** „Freies Bild“ rechts: Bild ohne Shot erzeugen (B3). Die Ergebnisse landen in der Galerie in der Mitte. */
export function FreeForm({ form, catalog, images, job, busy, onChange, onRun }: Props) {
  const { t } = useTranslation("studio")
  const set = (p: Partial<FreeFormState>) => onChange({ ...form, ...p })
  const running = job?.status === "running" || job?.status === "queued"
  const failed = job?.progress?.failed ?? 0
  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-3 text-xs" data-studio-panel="inspector" data-free-form>
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("free_title")}</h2>
      <p className="leading-relaxed text-[#9aa7bc]">{t("free_text")}</p>
      <label className="block">
        <Label>{t("free_prompt")}</Label>
        <textarea rows={4} maxLength={MAX_FREE_PROMPT} value={form.prompt} onChange={(e) => set({ prompt: e.target.value })}
          aria-label={t("free_prompt")} placeholder={t("free_prompt_placeholder")} className={fieldCls} />
      </label>
      <ModelPick kind="image" value={form.model} catalog={catalog} onChange={(model) => set({ model })} />
      <label className="block"><Label>{t("f.aspect")}</Label>
        <select value={form.aspect} onChange={(e) => set({ aspect: e.target.value })} aria-label={t("f.aspect")} className={fieldCls}>
          {ASPECTS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </label>
      <div>
        <Label>{t("free_count")}</Label>
        <div className="mt-1 flex gap-1" role="group" aria-label={t("free_count")}>
          {COUNTS.map((n) => (
            <button key={n} type="button" onClick={() => set({ count: n })} aria-pressed={n === form.count} data-free-count={n}
              className={`w-8 rounded-[4px] border py-1 font-bold ${n === form.count ? "border-[#69d7ff] bg-[#1c2940] text-[#69d7ff]" : "border-[rgb(var(--hh-s-rand,42_54_75))] text-[#9aa7bc] hover:text-[#e8eef8]"}`}>
              {n}
            </button>
          ))}
        </div>
      </div>
      {images.length > 0 && (
        <div>
          <Label>{t("free_refs", { max: MAX_FREE_REFS })}</Label>
          <div className="mt-1 grid max-h-40 grid-cols-4 gap-1 overflow-y-auto">
            {images.map((i) => {
              const on = form.refs.includes(i.rel)
              return (
                <button key={i.id} type="button" onClick={() => set({ refs: toggleRef(form.refs, i.rel) })} aria-pressed={on} data-free-ref={i.rel}
                  disabled={!on && form.refs.length >= MAX_FREE_REFS} title={i.name} aria-label={i.name}
                  className={`aspect-square overflow-hidden rounded-[3px] border disabled:opacity-30 ${on ? "border-[#69d7ff]" : "border-transparent hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))]"}`}>
                  <img src={fileUrl(i.abs)} alt="" loading="lazy" className="h-full w-full object-cover" />
                </button>
              )
            })}
          </div>
        </div>
      )}
      <p className="rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 leading-relaxed text-[#9aa7bc]">{t("free_cost")}</p>
      <button type="button" onClick={onRun} disabled={busy || running || !freeValid(form)} data-free-run
        className="flex items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 font-black text-[#08111c] disabled:opacity-50">
        {running ? <Loader2 size={13} className="animate-spin" /> : <ImagePlus size={13} />} {t("free_run", { count: form.count })}
       <Costs model={form.model} />
        </button>
      {running && job?.progress && <p className="text-[#ffb86b]" data-free-progress>{t("free_progress", { done: job.progress.done + job.progress.failed, total: job.progress.total })}</p>}
      {job?.status === "failed" && <p className="text-[#ff6b8a]" data-free-error>{jobText(t, job)}</p>}
      {job?.status === "done" && failed > 0 && <p className="text-[#ffb86b]">{t("free_partly", { failed })}</p>}
    </section>
  )
}
