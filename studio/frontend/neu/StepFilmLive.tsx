/** G5 Schritt 5 „Film“: Vorschau, Schalter Musik/Erzählstimme/Untertitel, „Film erzeugen“, Herunterladen. */
import { Download, Film, Loader2, Square } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { Costs } from "../Costs"
import { jobText } from "../jobLogic"
import type { Job } from "../planApi"
import type { RenderItem } from "../renderApi"
import { filmNotes, type FilmExtras } from "./guidedLogic"
import { FilmPreview } from "./FilmPreview"
import { ReplaceDialog } from "./ReplaceDialog"
import { StepHead } from "./ui"
import type { GuidedState } from "./useGuided"
import type { FilmActions } from "./useFilm"

function Toggle({ on, label, hint, onChange }: { on: boolean; label: string; hint: string; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-[#2a364b] p-3 hover:bg-[#1c2940]/40">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} className="mt-1 h-5 w-5 accent-[#3ddc97]" />
      <span><span className="block text-base font-bold text-[#f2f6fc]">{label}</span><span className="text-sm text-[#8d9ab0]">{hint}</span></span>
    </label>
  )
}

interface PanelProps {
  films: RenderItem[]
  job: Job | null
  extras: FilmExtras
  costs: string[]
  busy: boolean
  base: string
  onExtras: (x: FilmExtras) => void
  onMake: () => void
  onStop: () => void
}

export function FilmPanel({ films, job, extras, costs, busy, onExtras, onMake, onStop }: PanelProps) {
  const { t } = useTranslation("studio")
  const running = job && (job.status === "running" || job.status === "queued")
  const latest = films[0]
  const set = (k: keyof FilmExtras) => (v: boolean) => onExtras({ ...extras, [k]: v })
  return (
    <section className="space-y-3">
      <Toggle on={extras.music} label={t("guided.music_label")} hint={t("guided.music_hint")} onChange={set("music")} />
      <Toggle on={extras.voice} label={t("guided.voice_label")} hint={t("guided.voice_hint")} onChange={set("voice")} />
      <Toggle on={extras.subtitles} label={t("guided.subs_label")} hint={t("guided.subs_hint")} onChange={set("subtitles")} />
      {running ? (
        <div className="space-y-2 rounded-[10px] border border-[#69d7ff]/40 bg-[#69d7ff]/5 p-3 text-sm text-[#cdeeff]">
          <p className="flex items-center gap-2"><Loader2 size={16} className="animate-spin" /> {t(`guided.film_step.${job.progress?.current || "timeline"}`)}</p>
          <p className="text-xs text-[#8d9ab0]">{t("guided.film_n", { done: job.progress?.done ?? 0, total: job.progress?.total ?? 5 })}</p>
          <button type="button" onClick={onStop} className="inline-flex items-center gap-1 rounded-[6px] border border-[#46617f] px-3 py-1.5 text-xs font-bold text-[#e8eef8] hover:bg-[#1c2940]">
            <Square size={12} /> {t("guided.stop")}
          </button>
        </div>
      ) : (
        <button type="button" onClick={onMake} disabled={busy} data-guided-make-film
          className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-5 py-3 text-base font-black text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
          <Film size={18} /> {t(latest ? "guided.make_film_again" : "guided.make_film")}{costs.length > 0 && <Costs model={costs.filter(Boolean).join(", ") || undefined} />}
        </button>
      )}
      {job?.status === "failed" && <p className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{jobText(t, job)}</p>}
      {filmNotes(job).map((n) => <p key={n} className="rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{t(`guided.note.${n}`)}</p>)}
      {latest && (
        <div className="space-y-2 rounded-[10px] border border-[#3ddc97]/50 bg-[#3ddc97]/5 p-3">
          <p className="text-sm font-bold text-[#3ddc97]">{t("guided.film_done")}</p>
          <video src={fileUrl(latest.abs)} controls className="w-full rounded-[8px] bg-black" data-guided-film={latest.rel} />
          <a href={fileUrl(latest.abs)} download={latest.name}
            className="inline-flex items-center gap-2 rounded-[8px] bg-[#69d7ff] px-4 py-2.5 text-sm font-black text-[#06111c] hover:bg-[#8fe2ff]">
            <Download size={16} /> {t("guided.download")}
          </a>
          {films.length > 1 && (
            <details className="text-sm text-[#c3ccdd]">
              <summary className="cursor-pointer">{t("guided.earlier", { count: films.length - 1 })}</summary>
              <ul className="mt-2 space-y-1">
                {films.slice(1).map((f) => (
                  <li key={f.rel}><a href={fileUrl(f.abs)} download={f.name} className="text-[#69d7ff] underline">{f.created_at?.slice(0, 16).replace("T", " ") ?? f.name}</a></li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  )
}

export function StepFilmLive({ g, f }: { g: GuidedState; f: FilmActions }) {
  const { t } = useTranslation("studio")
  return (
    <div>
      <StepHead n={5} title={t("guided.step.5.title")} text={t("guided.film_head")} />
      {g.error && <p className="mb-3 rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{g.error}</p>}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(300px,1fr)]">
        <FilmPreview plan={g.plan} />
        <FilmPanel films={f.films} job={f.job} extras={f.extras} costs={f.costs} busy={g.busy} base={g.plan?.base ?? ""}
          onExtras={f.setExtras} onMake={() => void f.make()} onStop={() => void f.stop()} />
      </div>
      {f.asking && <ReplaceDialog count={0} busy={g.busy} title={t("guided.edited_title")} text={t("guided.edited_text")}
        yes={t("guided.edited_rebuild")} other={t("guided.edited_keep")} onReplace={() => void f.make(true)} onAppend={() => void f.make(false)} onClose={() => f.setAsking(false)} />}
    </div>
  )
}
