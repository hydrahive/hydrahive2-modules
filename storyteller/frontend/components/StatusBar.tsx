// Statusleiste: Speicherstand, Wörter (Szene/Kapitel/Buch), Tastenkürzel. Später: Tagesziel, Kosten.
import { useTranslation } from "react-i18next"
import { Keyboard } from "lucide-react"
import { bookWords, chapterWords, countWords, type Book, type Chapter, type Scene, type ScenePath } from "../model"
import type { SaveState } from "../useBook"

interface Props { book: Book; found: { path: ScenePath; scene: Scene; chapter: Chapter } | null; saveState: SaveState }

export function StatusBar({ book, found, saveState }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const n = (v: number) => v.toLocaleString(i18n.language)
  const save = {
    saved: <span className="text-emerald-400/80">● {t("saved")}</span>,
    saving: <span className="text-zinc-400">○ {t("saving")}</span>,
    failed: <span className="font-semibold text-red-400">● {t("save_failed")}</span>,
  }[saveState]
  return (
    <footer className="st-status flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/10 px-3 py-1.5 text-xs text-zinc-500" aria-live="polite">
      {save}
      {found && <span>{t("w_scene")} {n(countWords(found.scene.text))}</span>}
      {found && <span>{t("w_chapter")} {n(chapterWords(found.chapter))}</span>}
      <span>{t("w_book")} {n(bookWords(book))} {t("words_unit")}</span>
      <span className="ml-auto inline-flex items-center gap-1" title={t("shortcuts_list")}>
        <Keyboard className="h-3.5 w-3.5" />{t("shortcuts")}
      </span>
    </footer>
  )
}
