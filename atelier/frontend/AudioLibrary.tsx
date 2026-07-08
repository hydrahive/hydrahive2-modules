import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import type { AudioLibraryItem } from "./types"

interface Props {
  projectId: string
  items: AudioLibraryItem[]
  refAbsPath: (rel: string) => string
  onChanged: () => void
}

/** Bibliothek der generierten Tracks: Player + Prompt + Löschen.
 *  refAbsPath (root + rel) kommt von AudioPanel, wie bei ImageGalleryPanel/ClipLibraryPanel. */
export function AudioLibrary({ projectId, items, refAbsPath, onChanged }: Props) {
  const { t } = useTranslation("atelier")

  async function remove(rel: string) {
    if (!confirm(t("audio_delete_track_confirm"))) return
    await atelierApi.deleteAudioTrack(projectId, rel)
    onChanged()
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-200">🎵 {t("audio_library")}</h3>
      {items.length === 0 && <p className="text-xs text-slate-500">{t("audio_library_empty")}</p>}
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li key={item.rel} className="group rounded border border-slate-700 bg-slate-800/50 p-2 flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-300 truncate flex-1">{item.prompt || t("untitled")}</span>
              <button
                onClick={() => remove(item.rel)}
                title={t("delete")}
                className="text-xs text-slate-500 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
              >
                🗑️
              </button>
            </div>
            <audio src={fileUrl(refAbsPath(item.rel))} controls preload="metadata" className="w-full h-8" />
          </li>
        ))}
      </ul>
    </div>
  )
}
