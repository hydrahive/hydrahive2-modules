// Liste der Bibliothek: Titel, Untertitel (Prompt/Modell/Dauer) zum Nachschlagen.
import { Download, Music, Trash2, Video } from "lucide-react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { trackSubtitle } from "./mediaUtils"
import type { LibraryPermissions, MediaKind, Track } from "./types"
import leerBild from "./assets/leer.webp"

export function TrackList({ projectId, kind, tracks, activeId, permissions, onSelect, onRemove, tall = false }: {
  projectId: string
  kind: MediaKind
  tracks: Track[]
  activeId?: number
  permissions: LibraryPermissions
  onSelect: (track: Track) => void
  onRemove: (id: number) => void
  tall?: boolean
}) {
  const { t } = useTranslation("musicplayer")
  if (!tracks.length) {
    return (
      <div className="rounded-[4px] border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))]"><div className="flex flex-col items-center gap-2 py-4 text-center"><img src={leerBild} alt="" loading="lazy" draggable={false} className="mx-auto h-20 w-20 select-none object-contain" /><p className="text-[11px] text-[#9aa7bc]">{t("mp_empty")}</p></div></div>
    )
  }
  const Icon = kind === "video" ? Video : Music
  return (
    <div className={`${tall ? "max-h-[28rem]" : "max-h-56"} space-y-1 overflow-y-auto pr-1`}>
      {tracks.map((track) => {
        const active = activeId === track.id
        const subtitle = trackSubtitle(track.meta)
        return (
          <div
            key={track.id}
            className={`flex min-w-0 items-center rounded-[4px] border ${active
              ? "border-fuchsia-400/35 bg-fuchsia-500/10"
              : "border-transparent bg-[rgb(var(--hh-s-innen,17_24_39))] hover:border-[rgb(var(--hh-s-rand-hover,42_54_75))]"}`}
          >
            <button type="button" onClick={() => onSelect(track)} className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left">
              <Icon size={12} className="shrink-0 text-[#9aa7bc]" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs text-[#c4cedd]" title={track.title}>{track.title}</span>
                {subtitle.text && (
                  <span className="block truncate text-[10px] text-[#9aa7bc]" title={subtitle.promptTitle}>{subtitle.text}</span>
                )}
              </span>
            </button>
            <button
              type="button"
              onClick={() => void musicApi.download(projectId, track).catch(() => {})}
              title={t("mp_download", { title: track.title })}
              aria-label={t("mp_download", { title: track.title })}
              className="p-2 text-[#64748b] hover:text-cyan-200"
            >
              <Download size={12} />
            </button>
            {permissions.can_delete && (
              <button
                type="button"
                onClick={() => onRemove(track.id)}
                title={t("mp_delete", { title: track.title })}
                aria-label={t("mp_delete", { title: track.title })}
                className="p-2 text-[#64748b] hover:text-rose-300"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
