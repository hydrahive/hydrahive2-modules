/** G1 Schritt „Idee“: eine Frage, Art/Länge/Format als Knöpfe, „Geschichte vorschlagen“. */
import { Loader2, Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Costs } from "../Costs"
import { FILM_KINDS, type FilmKind } from "./guidedLogic"
import { BigButton, Notice } from "./ui"

interface Props {
  idea: string
  kind: FilmKind
  length: number
  format: string
  hasScenes: boolean
  busy: boolean
  error: string | null
  /** Text-Modell aus dem Drehbuch (leer = Standard des Servers) */
  model: string
  onIdea: (v: string) => void
  onKind: (v: FilmKind) => void
  onLength: (v: number) => void
  onFormat: (v: string) => void
  onRun: () => void
  onSelf: () => void
}

const pill = (on: boolean) => `rounded-full px-4 py-2 text-sm font-semibold ${on ? "bg-[#69d7ff] text-[#06111c]" : "border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#c3ccdd] hover:bg-[#1c2940]"}`

export function IdeaForm(p: Props) {
  const { t } = useTranslation("studio")
  return (
    <section className="space-y-4 rounded-[12px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,14_20_32))] p-5">
      <label className="block">
        <span className="text-lg font-bold text-[#f2f6fc]">{t("guided.idea_question")}</span>
        <textarea value={p.idea} onChange={(e) => p.onIdea(e.target.value)} rows={4} maxLength={2000} placeholder={t("guided.idea_placeholder")}
          className="mt-2 w-full rounded-[8px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-grund,8_11_17))] p-3 text-base text-[#e8eef8] outline-none focus:border-[#69d7ff]" />
      </label>
      {!p.idea && <button type="button" onClick={() => p.onIdea(t("guided.example_text"))} className="text-sm text-[#69d7ff] underline">{t("guided.example")}</button>}
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-32 text-sm text-[#9aa7bc]">{t("guided.kind_label")}</span>
        {FILM_KINDS.map((k) => <button key={k} type="button" className={pill(p.kind === k)} aria-pressed={p.kind === k} onClick={() => p.onKind(k)}>{t(`guided.kind.${k}`)}</button>)}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-32 text-sm text-[#9aa7bc]">{t("guided.len_label")}</span>
        {[0, 1, 2].map((i) => <button key={i} type="button" className={pill(p.length === i)} aria-pressed={p.length === i} onClick={() => p.onLength(i)}>{t(`guided.len.${i}`)}</button>)}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-32 text-sm text-[#9aa7bc]">{t("guided.format_label")}</span>
        {([["16:9", "wide"], ["9:16", "tall"]] as const).map(([v, k]) => (
          <button key={v} type="button" data-guided-format={v} aria-pressed={p.format === v} className={pill(p.format === v)} onClick={() => p.onFormat(v)}>{t(`guided.format.${k}`)}</button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button type="button" onClick={p.onRun} disabled={p.busy || !p.idea.trim()} data-guided-suggest
          className="inline-flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2.5 text-sm font-bold text-[#04140d] hover:bg-[#5ee6aa] disabled:opacity-50">
          {p.busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {t(p.hasScenes ? "guided.suggest_again" : "guided.suggest")}<Costs model={p.model || undefined} />
        </button>
        {!p.hasScenes && <BigButton tone="plain" onClick={p.onSelf} disabled={p.busy}><Plus size={16} /> {t("guided.self")}</BigButton>}
      </div>
      {p.busy && <p className="text-sm text-[#c3ccdd]">{t("guided.writing")}</p>}
      {p.error && <Notice>{p.error}</Notice>}
    </section>
  )
}
