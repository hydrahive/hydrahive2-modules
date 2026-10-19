import { Download, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { LibraryItem } from "./api"
import { downloadName } from "./mediaLogic"

const btn = "flex items-center justify-center gap-1.5 rounded-[4px] border px-2.5 py-1.5 text-xs font-bold"

/** Bibliothek → gewähltes Medium: Herunterladen und (nur eigene Dateien) Löschen (C1). */
export function MediaActions({ item, onDelete }: { item: LibraryItem; onDelete: () => void }) {
  const { t } = useTranslation("studio")
  if (item.kind === "element") return null
  return (
    <div className="mt-3 space-y-1.5" data-media-actions>
      <div className="flex gap-1.5">
        <a href={fileUrl(item.abs)} download={downloadName(item)} className={`${btn} flex-1 border-[#46617f] text-[#69d7ff] hover:bg-[#1c2940]`}>
          <Download size={13} /> {t("media_download")}
        </a>
        {item.deletable && (
          <button type="button" onClick={onDelete} data-media-delete className={`${btn} flex-1 border-[#ff6b8a]/50 text-[#ff6b8a] hover:bg-[#ff6b8a]/10`}>
            <Trash2 size={13} /> {t("media_delete")}
          </button>
        )}
      </div>
      {!item.deletable && <p className="text-[10px] leading-relaxed text-[#68758a]">{t("media_not_own", { source: t(`source.${item.source}`) })}</p>}
    </div>
  )
}
