import { Loader2, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { IDEA_LENGTHS, type IdeaLength } from "./draftApi"
import { ideaValid, MAX_IDEA, MAX_STYLE } from "./draftLogic"
import { fieldCls, Label } from "./formParts"
import { Costs } from "./Costs"

interface Props {
  idea: string
  length: IdeaLength
  style: string
  busy: boolean
  error: string | null
  onIdea: (v: string) => void
  onLength: (v: IdeaLength) => void
  onStyle: (v: string) => void
  onRun: () => void
  onClose: () => void
}

/** „Aus einer Idee“: ein bis drei Sätze, ungefähre Länge, Stil. Die KI schreibt daraus einen Entwurf (noch nichts gespeichert). */
export function IdeaForm({ idea, length, style, busy, error, onIdea, onLength, onStyle, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-idea-form>
      <h3 className="text-sm font-black text-[#e8eef8]">{t("idea_title")}</h3>
      <p className="leading-relaxed text-[#8d9ab0]">{t("idea_text")}</p>
      <label className="block">
        <Label>{t("idea_label")}</Label>
        <textarea rows={4} maxLength={MAX_IDEA} value={idea} onChange={(e) => onIdea(e.target.value)} disabled={busy}
          placeholder={t("idea_placeholder")} aria-label={t("idea_label")} data-field="idea" className={fieldCls} />
      </label>
      <div>
        <Label>{t("idea_length")}</Label>
        <div className="mt-1 flex gap-1" role="group" aria-label={t("idea_length")}>
          {IDEA_LENGTHS.map((l) => (
            <button key={l} type="button" onClick={() => onLength(l)} disabled={busy} aria-pressed={l === length} data-idea-length={l}
              className={`rounded-[4px] border px-2.5 py-1 font-bold ${l === length ? "border-[#69d7ff] bg-[#1c2940] text-[#69d7ff]" : "border-[#2a364b] text-[#8d9ab0] hover:text-[#e8eef8]"}`}>
              {t(`idea_len.${l}`)}
            </button>
          ))}
        </div>
      </div>
      <label className="block">
        <Label>{t("idea_style")}</Label>
        <input value={style} maxLength={MAX_STYLE} onChange={(e) => onStyle(e.target.value)} disabled={busy}
          placeholder={t("idea_style_placeholder")} aria-label={t("idea_style")} data-field="idea_style" className={fieldCls} />
      </label>
      <p className="rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 leading-relaxed text-[#8d9ab0]">{busy ? t("idea_busy") : t("idea_cost")}</p>
      {error && <p className="text-[#ff6b8a]" data-idea-error>{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
        <button type="button" onClick={onRun} disabled={busy || !ideaValid(idea, style)} data-idea-run
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} {t("idea_run")}
         <Costs />
        </button>
      </div>
    </div>
  )
}
