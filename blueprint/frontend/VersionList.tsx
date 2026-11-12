import { History, X } from "lucide-react"
import { formatStamp } from "./boardView"
import { BUTTON, RAND, SIDE_PANEL } from "./styles"
import type { T } from "./texts.de"
import type { BoardVersion } from "./types"

interface Props {
  /** null: wird noch geladen. */
  versions: BoardVersion[] | null
  error: boolean
  /** Meldung nach einem fehlgeschlagenen Wiederherstellen. */
  message?: string | null
  busy: boolean
  locale: string
  t: T
  onRestore: (versionId: number) => void
  onClose: () => void
}

/** Rechte Spalte: frühere Fassungen des Boards, neueste zuerst, jede wiederherstellbar. */
export function VersionList({ versions, error, message, busy, locale, t, onRestore, onClose }: Props) {
  return (
    <aside aria-label={t("versions_title")} className={`${SIDE_PANEL} flex flex-col`}>
      <div className={`flex items-center gap-2 border-b ${RAND} px-4 py-2.5`}>
        <History size={14} className="text-[#c8d2df]" aria-hidden />
        <span className="flex-1 text-sm font-semibold text-[#e8eef8]">{t("versions_title")}</span>
        <button type="button" onClick={onClose} title={t("close")} aria-label={t("close")}
          className="rounded p-1 text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] hover:text-[#e8eef8]">
          <X size={14} aria-hidden />
        </button>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4 text-xs text-[#9aa7bc]">
        <p>{t("versions_restore_hint")}</p>
        {error && <p role="alert" className="text-rose-200">{t("versions_load_error")}</p>}
        {message && <p role="alert" className="text-rose-200">{message}</p>}
        {!error && versions === null && <p>{t("status_loading")}</p>}
        {!error && versions?.length === 0 && <p>{t("versions_empty")}</p>}
        {!error && versions !== null && versions.length > 0 && (
          <ul className="space-y-2">
            {versions.map((version) => (
              <li key={version.id}
                className={`space-y-1.5 rounded-lg border ${RAND} bg-[rgb(var(--hh-s-box,21_28_43))] p-2.5`}>
                <p className="font-semibold text-[#e8eef8]">{formatStamp(version.created_at, locale)}</p>
                <p>{t("count_nodes", { n: version.node_count })} · {t(`version_source_${version.source}`)}</p>
                <button type="button" onClick={() => onRestore(version.id)} disabled={busy} className={BUTTON}>
                  {t("versions_restore")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}
