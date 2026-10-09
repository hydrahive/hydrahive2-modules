// C1 – gelöschte Kapitel im Papierkorb des Buchs (Teil des Papierkorbs im Navigator): Titel, Anzahl Szenen, Wörter,
// „Wiederherstellen“ (ganzes Kapitel an die alte Stelle). Leser sehen nur die Liste.
import { useTranslation } from "react-i18next"
import { RotateCcw } from "lucide-react"
import { isFiction } from "../bookFactory"
import type { TrashChapter } from "../trashApi"

interface Props {
  rows: TrashChapter[]
  kind: Parameters<typeof isFiction>[0]
  canWrite: boolean
  onRestore: (c: TrashChapter) => void
}

export function TrashChapters({ rows, kind, canWrite, onRestore }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const unit = isFiction(kind) ? "scene" : "section"
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "short", timeStyle: "short" })
  if (!rows.length) return null
  return (
    <ul className="mt-1 space-y-1">
      {rows.map((c) => (
        <li key={c.id} className="st-trash-chapter rounded border border-white/10 px-2 py-1 text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate font-semibold text-zinc-300">{t("trash_chapter_label", { title: c.title })}</span>
            {canWrite && <button onClick={() => onRestore(c)} title={t("trash_restore")}
              className="st-trash-restore-chapter inline-flex items-center gap-1 text-violet-300 hover:underline">
              <RotateCcw className="h-3 w-3" />{t("trash_restore")}</button>}
          </div>
          <p className="text-[11px] text-zinc-500">
            {t("trash_deleted_at", { when: fmt(c.deleted_at) })} · {t(`trash_chapter_n_${unit}`, { count: c.scenes })} · {t("words_n", { n: c.words })}
          </p>
        </li>
      ))}
    </ul>
  )
}
