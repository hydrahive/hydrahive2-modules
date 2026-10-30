import { BookOpen, Download, Loader2, PenLine, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"

interface Props {
  atelier: boolean
  /** Bücher im Storyteller des Projekts */
  books: number
  busy: boolean
  onStart: () => void
  onImport: () => void
  onIdea: () => void
  onBook: () => void
}

/** Planen ohne Szenen: „So fängst du an“ – was ein Film hier ist und der erste Schritt als Knopf. */
export function StartCard({ atelier, books, busy, onStart, onImport, onIdea, onBook }: Props) {
  const { t } = useTranslation("studio")
  const way = "flex flex-col items-start gap-1 rounded-[6px] border p-3 text-left"
  return (
    <div className="mx-auto w-full max-w-xl space-y-3 rounded-[6px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-tief,14_20_32))] p-4" data-studio-start>
      <h2 className="text-base font-black text-[#e8eef8]">{t("start_title")}</h2>
      <p className="text-xs leading-relaxed text-[#c3ccdd]">{t("start_text")}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className={`${way} border-[#69d7ff]/50 bg-[#69d7ff]/5`}>
          <button type="button" onClick={onIdea} disabled={busy}
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 text-xs font-black text-[#08111c] disabled:opacity-50">
            <Sparkles size={13} /> {t("start_idea")}
          </button>
          <span className="text-[11px] leading-relaxed text-[#9aa7bc]">{t("start_idea_hint")}</span>
        </div>
        {books > 0 && (
          <div className={`${way} border-[#69d7ff]/50 bg-[#69d7ff]/5`}>
            <button type="button" onClick={onBook} disabled={busy}
              className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 text-xs font-black text-[#08111c] disabled:opacity-50">
              <BookOpen size={13} /> {t("start_book")}
            </button>
            <span className="text-[11px] leading-relaxed text-[#9aa7bc]">{t("start_book_hint")}</span>
          </div>
        )}
        <div className={`${way} border-[rgb(var(--hh-s-rand,42_54_75))]`}>
          <button type="button" onClick={onStart} disabled={busy}
            className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff] px-3 py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <PenLine size={13} />} {t("start_self")}
          </button>
          <span className="text-[11px] leading-relaxed text-[#9aa7bc]">{t("start_self_hint")}</span>
        </div>
        {atelier && (
          <div className={`${way} border-[rgb(var(--hh-s-rand,42_54_75))]`}>
            <button type="button" onClick={onImport}
              className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff] px-3 py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#1c2940]">
              <Download size={13} /> {t("start_atelier")}
            </button>
            <span className="text-[11px] leading-relaxed text-[#9aa7bc]">{t("start_atelier_hint")}</span>
          </div>
        )}
      </div>
    </div>
  )
}
