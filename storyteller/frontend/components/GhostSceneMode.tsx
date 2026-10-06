// KI-Modus „Szene schreiben“ (Ghostwriter G1): Die KI schreibt die Szene aus Zusammenfassung,
// Steckbriefen und Gedächtnis. Alles je Buch einstellbar (Modell, Länge, Stil), nichts fest eingebaut.
// Ergebnis erst als Vorschlag; „Annehmen“ setzt es ein (vorher Schnappschuss, wenn schon Text da war).
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, Feather, Loader2, RotateCcw, Square, X } from "lucide-react"
import type { Scene } from "../model"
import type { BookState } from "../useBook"
import { useGhostScene } from "../useGhostScene"
import { ModelChooser } from "./ModelChooser"

const LENGTHS = [800, 1500, 2500] as const
const field = "w-full rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600"

interface Props { state: BookState; scene: Scene; onGoScene: () => void }

export function GhostSceneMode({ state, scene, onGoScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { book } = state
  const g = book.ghost
  const [length, setLength] = useState<number>(g.length_words || 0)
  const run = useGhostScene(state, scene, length)
  const setGhost = (patch: Partial<typeof g>) => state.change((b) => ({ ...b, ghost: { ...b.ghost, ...patch } }))
  const n = (v: number) => v.toLocaleString(i18n.language)
  const running = run.phase === "running"
  const noSummary = !scene.summary.trim()

  return (
    <div className="st-ghost space-y-3">
      <p className="text-xs text-zinc-400">{t("ghost_intro")}</p>
      <ModelChooser value={g.model} onChange={(model) => setGhost({ model })} label={t("ghost_model_label")}
        fallback={book.model} />
      <fieldset className="space-y-1 text-xs text-zinc-400" disabled={running}>
        <legend>{t("ghost_length")}</legend>
        <div className="flex flex-wrap gap-1">
          {LENGTHS.map((w) => (
            <button key={w} type="button" aria-pressed={length === w} onClick={() => { setLength(w); setGhost({ length_words: w }) }}
              className={`rounded-lg border px-2 py-1 ${length === w ? "border-violet-400 bg-violet-500/15 text-violet-100" : "border-white/10 hover:bg-white/5"}`}>
              {t(`ghost_len_${w}`)}
            </button>
          ))}
          <input type="number" min={200} max={6000} step={100} value={length || ""} placeholder={t("ghost_len_free")}
            aria-label={t("ghost_len_free")} className={`${field} w-28`}
            onChange={(e) => setLength(Number(e.target.value) || 0)}
            onBlur={() => { if (length >= 200 && length <= 6000) setGhost({ length_words: length }) }} />
        </div>
      </fieldset>
      <label className="block space-y-1 text-xs text-zinc-400"><span>{t("ghost_style")}</span>
        <textarea className={`${field} min-h-[52px]`} defaultValue={g.style} maxLength={2000} placeholder={t("ghost_style_ph")}
          disabled={running} onBlur={(e) => { if (e.target.value !== g.style) setGhost({ style: e.target.value }) }} />
      </label>

      {noSummary && (
        <div className="st-ghost-hint space-y-1 rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">
          <p>{t("ghost_need_summary")}</p>
          <button onClick={onGoScene} className="font-semibold underline hover:text-amber-100">{t("ghost_go_summary")}</button>
        </div>
      )}
      {!noSummary && scene.text.trim() && (run.phase === "idle" || run.phase === "accepted") && <p className="text-xs text-zinc-500">{t("ghost_has_text")}</p>}
      {run.estimate && run.phase === "idle" && (
        <p className="st-ghost-estimate text-[11px] text-zinc-500">
          {t("ghost_estimate", { sections: run.estimate.sections, out: n(run.estimate.output_tokens), in: n(run.estimate.input_tokens),
            model: run.estimate.model || t("ghost_model_default") })}
        </p>
      )}

      <div className="flex gap-2">
        {!running ? (
          <button onClick={() => { void run.start() }} disabled={noSummary || length < 200 || run.phase === "ready"}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40">
            <Feather className="h-4 w-4" />{t("ghost_start")}
          </button>
        ) : (
          <button onClick={run.stop} className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-200 hover:bg-white/5">
            <Square className="h-4 w-4" />{t("ghost_stop")}
          </button>
        )}
      </div>
      {run.error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200" role="alert">
        {t(`ai_err_${run.error.code}`, { defaultValue: "" }) || t("ai_err_llm_failed", { message: run.error.message || run.error.code })}
      </p>}

      {(running || run.phase === "ready") && (
        <section className="st-ghost-result space-y-2 rounded-xl border border-violet-400/30 bg-violet-500/5 p-3" aria-live="polite">
          <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300">
            {running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {running ? t("ghost_writing", { n: n(run.text.split(/\s+/).filter(Boolean).length) }) : t("ghost_ready", { n: n(run.done?.words ?? 0) })}
          </h3>
          <div className="max-h-80 overflow-y-auto whitespace-pre-wrap font-serif text-sm leading-relaxed text-zinc-200">{run.text}</div>
          {run.done?.model && <p className="font-mono text-[10px] text-zinc-500">{run.done.model}</p>}
          {run.phase === "ready" && (
            <div className="flex flex-wrap gap-2 pt-1">
              <button onClick={() => { void run.accept() }} className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500">
                <Check className="h-4 w-4" />{scene.text.trim() ? t("ghost_accept_replace") : t("ghost_accept")}
              </button>
              <button onClick={run.reject} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5">
                <X className="h-4 w-4" />{t("ghost_reject")}
              </button>
              <button onClick={() => { void run.start() }} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5">
                <RotateCcw className="h-4 w-4" />{t("ai_again")}
              </button>
            </div>
          )}
        </section>
      )}
      {run.phase === "accepted" && <p className="text-xs text-emerald-300">{t("ghost_accepted")}</p>}
    </div>
  )
}
